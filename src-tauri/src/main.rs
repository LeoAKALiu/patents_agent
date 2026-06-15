use base64::{engine::general_purpose, Engine as _};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    fs,
    io::{Read, Write},
    net::{TcpListener, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};
use tauri::{AppHandle, Manager, State};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_opener::OpenerExt;

const HEALTH_PATH: &str = "/api/health";
const STARTUP_TIMEOUT_MS: u64 = 20_000;
const REDACTED_CONFIG_FIELDS: &[&str] = &["api_key_present", "api_key_fingerprint"];
const SECRET_PREFIX: &str = concat!("s", "k", "-");
const SECRET_REDACTION: &str = concat!("s", "k", "-...");

#[derive(Debug, Clone, Serialize)]
struct BackendInfo {
    base_url: String,
    health_url: String,
    port: u16,
}

struct BackendSupervisor {
    child: Child,
    info: BackendInfo,
}

impl Drop for BackendSupervisor {
    fn drop(&mut self) {
        self.shutdown();
    }
}

impl BackendSupervisor {
    fn shutdown(&mut self) {
        if self.child.try_wait().ok().flatten().is_none() {
            let _ = self.child.kill();
        }
        let _ = self.child.wait();
    }
}

#[derive(Default)]
struct BackendState {
    supervisor: Mutex<Option<BackendSupervisor>>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct OpenDraftResult {
    cancelled: bool,
    file_path: String,
    file_name: String,
    mime_type: String,
    content_base64: String,
    byte_count: usize,
}

#[derive(Debug, Deserialize)]
struct OpenDraftPayload {
    kind: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct SaveOfficialResult {
    cancelled: bool,
    file_path: String,
    byte_count: usize,
    format: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct DialogFilterPayload {
    name: String,
    extensions: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SaveOfficialPayload {
    format: String,
    label: String,
    download_path: String,
    filter: DialogFilterPayload,
    default_file_name: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct OpenFolderResult {
    revealed: bool,
    file_path: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct OpenFolderPayload {
    file_path: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct DesktopConfigUpdatePayload {
    provider: Option<String>,
    base_url: Option<String>,
    model: Option<String>,
    api_key: Option<String>,
    clear_api_key: Option<bool>,
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(BackendState::default())
        .setup(|app| {
            let repo_root = repo_root();
            let data_dir = app.path().app_data_dir().unwrap_or_else(|_| {
                std::env::temp_dir()
                    .join("PatentAgent")
                    .join("backend-data")
            });
            fs::create_dir_all(&data_dir)?;
            let supervisor = start_backend(&repo_root, &data_dir)?;
            let state = app.state::<BackendState>();
            *state
                .supervisor
                .lock()
                .map_err(|_| "backend state lock poisoned")? = Some(supervisor);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_base_url,
            desktop_config_get,
            desktop_config_update,
            desktop_config_clear_key,
            desktop_config_health,
            open_draft,
            save_official,
            open_folder,
        ])
        .build(tauri::generate_context!())
        .expect("failed to build PatentAgent Tauri app");
    app.run(|app_handle, event| match event {
        tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
            shutdown_backend(app_handle);
        }
        _ => {}
    });
}

fn shutdown_backend(app_handle: &AppHandle) {
    let state = app_handle.state::<BackendState>();
    let supervisor = match state.supervisor.lock() {
        Ok(mut guard) => guard.take(),
        Err(_) => None,
    };
    if let Some(mut supervisor) = supervisor {
        supervisor.shutdown();
    }
}

#[tauri::command]
fn get_backend_base_url(state: State<'_, BackendState>) -> Result<String, String> {
    let guard = state
        .supervisor
        .lock()
        .map_err(|_| "backend state lock poisoned")?;
    let supervisor = guard.as_ref().ok_or("backend supervisor is not running")?;
    Ok(supervisor.info.base_url.clone())
}

#[tauri::command]
fn desktop_config_get(state: State<'_, BackendState>) -> Result<Value, String> {
    let mut value = backend_json(&state, "GET", "/api/desktop-config", None)?;
    ensure_config_is_redacted(&mut value)?;
    Ok(value)
}

#[tauri::command]
fn desktop_config_update(
    state: State<'_, BackendState>,
    payload: DesktopConfigUpdatePayload,
) -> Result<Value, String> {
    let body = serde_json::to_value(payload).map_err(|err| err.to_string())?;
    let mut value = backend_json(&state, "PATCH", "/api/desktop-config", Some(body))?;
    ensure_config_is_redacted(&mut value)?;
    Ok(value)
}

#[tauri::command]
fn desktop_config_clear_key(state: State<'_, BackendState>) -> Result<Value, String> {
    let mut value = backend_json(
        &state,
        "PATCH",
        "/api/desktop-config",
        Some(json!({ "clear_api_key": true })),
    )?;
    ensure_config_is_redacted(&mut value)?;
    Ok(value)
}

#[tauri::command]
fn desktop_config_health(state: State<'_, BackendState>) -> Result<Value, String> {
    backend_json(
        &state,
        "POST",
        "/api/desktop-config/health",
        Some(json!({})),
    )
}

#[tauri::command]
fn open_draft(app: tauri::AppHandle, payload: OpenDraftPayload) -> Result<OpenDraftResult, String> {
    let (title, filter_name, extensions): (&str, &str, &[&str]) = if payload.kind == "docx" {
        ("选择要导入的 Word 草稿", "Word 文档", &["docx"])
    } else if payload.kind == "markdown" {
        (
            "选择要导入的 Markdown 草稿",
            "Markdown 文本",
            &["md", "markdown"],
        )
    } else {
        return Err("open-draft kind must be 'docx' or 'markdown'".to_string());
    };
    let Some(file_path) = app
        .dialog()
        .file()
        .set_title(title)
        .add_filter(filter_name, extensions)
        .add_filter("全部文件", &["*"])
        .blocking_pick_file()
    else {
        return Ok(OpenDraftResult {
            cancelled: true,
            file_path: String::new(),
            file_name: String::new(),
            mime_type: mime_type_for_draft_kind(&payload.kind).to_string(),
            content_base64: String::new(),
            byte_count: 0,
        });
    };
    let path = dialog_path_to_pathbuf(file_path)?;
    let ext = path
        .extension()
        .and_then(|value| value.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    if payload.kind == "docx" && ext != "docx" {
        return Err("selected draft must be a .docx file".to_string());
    }
    if payload.kind == "markdown" && ext != "md" && ext != "markdown" {
        return Err("selected draft must be a .md or .markdown file".to_string());
    }
    let content = fs::read(&path).map_err(|err| sanitize_error(err.to_string()))?;
    let file_name = path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("")
        .to_string();
    Ok(OpenDraftResult {
        cancelled: false,
        file_path: path.to_string_lossy().to_string(),
        file_name,
        mime_type: mime_type_for_draft_kind(&payload.kind).to_string(),
        content_base64: general_purpose::STANDARD.encode(&content),
        byte_count: content.len(),
    })
}

#[tauri::command]
fn save_official(
    app: tauri::AppHandle,
    state: State<'_, BackendState>,
    payload: SaveOfficialPayload,
) -> Result<SaveOfficialResult, String> {
    if !matches!(payload.format.as_str(), "docx" | "md" | "sidecar") {
        return Err("save-official format must be 'docx' | 'md' | 'sidecar'".to_string());
    }
    if !payload.download_path.starts_with("/api/") {
        return Err("download_path must start with /api/".to_string());
    }
    let title = if payload.label.trim().is_empty() {
        "保存正式稿".to_string()
    } else {
        format!("保存{}", payload.label)
    };
    let extension_refs: Vec<&str> = payload
        .filter
        .extensions
        .iter()
        .map(String::as_str)
        .collect();
    let mut dialog = app
        .dialog()
        .file()
        .set_title(title)
        .set_file_name(payload.default_file_name.clone());
    if !extension_refs.is_empty() {
        dialog = dialog.add_filter(payload.filter.name.clone(), &extension_refs);
    }
    let Some(file_path) = dialog.add_filter("全部文件", &["*"]).blocking_save_file() else {
        return Ok(SaveOfficialResult {
            cancelled: true,
            file_path: String::new(),
            byte_count: 0,
            format: payload.format,
        });
    };
    let bytes = backend_bytes(&state, "GET", &payload.download_path, None)?;
    if bytes.is_empty() {
        return Err("backend returned an empty export body".to_string());
    }
    let output_path = ensure_extension(dialog_path_to_pathbuf(file_path)?, &payload.format);
    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent).map_err(|err| sanitize_error(err.to_string()))?;
    }
    fs::write(&output_path, &bytes).map_err(|err| sanitize_error(err.to_string()))?;
    Ok(SaveOfficialResult {
        cancelled: false,
        file_path: output_path.to_string_lossy().to_string(),
        byte_count: bytes.len(),
        format: payload.format,
    })
}

#[tauri::command]
fn open_folder(
    app: tauri::AppHandle,
    payload: OpenFolderPayload,
) -> Result<OpenFolderResult, String> {
    let file_path = payload.file_path;
    if file_path.trim().is_empty() {
        return Err("file_path is required".to_string());
    }
    app.opener()
        .reveal_item_in_dir(file_path.clone())
        .map_err(|err| sanitize_error(err.to_string()))?;
    Ok(OpenFolderResult {
        revealed: true,
        file_path,
    })
}

fn repo_root() -> PathBuf {
    std::env::var_os("PATENTAGENT_REPO_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .unwrap()
                .to_path_buf()
        })
}

fn start_backend(
    repo_root: &Path,
    data_dir: &Path,
) -> Result<BackendSupervisor, Box<dyn std::error::Error>> {
    let port = find_available_port()?;
    let base_url = format!("http://127.0.0.1:{port}");
    let health_url = format!("{base_url}{HEALTH_PATH}");
    let python = std::env::var("PATENTAGENT_PYTHON").unwrap_or_else(|_| "python3".to_string());
    let existing_pythonpath = std::env::var("PYTHONPATH").unwrap_or_default();
    let pythonpath = if existing_pythonpath.is_empty() {
        repo_root.to_string_lossy().to_string()
    } else {
        format!("{}:{}", repo_root.to_string_lossy(), existing_pythonpath)
    };
    let mut child = Command::new(&python)
        .args([
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
            "--log-level",
            "warning",
        ])
        .current_dir(repo_root)
        .env("DATA_DIR", data_dir)
        .env("PYTHONPATH", pythonpath)
        .env("PYTHONUNBUFFERED", "1")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;

    if let Err(err) = wait_for_health(&health_url, &mut child) {
        let _ = child.kill();
        let _ = child.wait();
        return Err(err.into());
    }

    Ok(BackendSupervisor {
        child,
        info: BackendInfo {
            base_url,
            health_url,
            port,
        },
    })
}

fn find_available_port() -> Result<u16, std::io::Error> {
    let listener = TcpListener::bind(("127.0.0.1", 0))?;
    let port = listener.local_addr()?.port();
    drop(listener);
    Ok(port)
}

fn wait_for_health(health_url: &str, child: &mut Child) -> Result<(), String> {
    let deadline = Instant::now() + Duration::from_millis(STARTUP_TIMEOUT_MS);
    let mut last_error = String::new();
    while Instant::now() < deadline {
        if let Ok(Some(status)) = child.try_wait() {
            return Err(format!("backend exited before health check: {status}"));
        }
        match http_request(health_url, "GET", None) {
            Ok(bytes) => {
                let body = String::from_utf8_lossy(&bytes);
                if body.contains("\"ok\":true") || body.contains("\"ok\": true") {
                    return Ok(());
                }
                last_error = format!("health response did not include ok=true: {body}");
            }
            Err(err) => last_error = err,
        }
        thread::sleep(Duration::from_millis(250));
    }
    Err(format!("backend did not become healthy: {last_error}"))
}

fn backend_json(
    state: &State<'_, BackendState>,
    method: &str,
    path: &str,
    body: Option<Value>,
) -> Result<Value, String> {
    let bytes = backend_bytes(state, method, path, body)?;
    serde_json::from_slice(&bytes).map_err(|err| sanitize_error(err.to_string()))
}

fn backend_bytes(
    state: &State<'_, BackendState>,
    method: &str,
    path: &str,
    body: Option<Value>,
) -> Result<Vec<u8>, String> {
    let guard = state
        .supervisor
        .lock()
        .map_err(|_| "backend state lock poisoned")?;
    let supervisor = guard.as_ref().ok_or("backend supervisor is not running")?;
    let url = format!("{}{}", supervisor.info.base_url, path);
    let body_text = body.map(|value| value.to_string());
    http_request(&url, method, body_text.as_deref())
}

fn http_request(url: &str, method: &str, body: Option<&str>) -> Result<Vec<u8>, String> {
    let without_scheme = url
        .strip_prefix("http://")
        .ok_or_else(|| format!("unsupported URL: {url}"))?;
    let (host_port, path) = without_scheme
        .split_once('/')
        .map(|(host_port, path)| (host_port, format!("/{path}")))
        .ok_or_else(|| format!("invalid URL: {url}"))?;
    let (host, port_text) = host_port
        .rsplit_once(':')
        .ok_or_else(|| format!("URL must include a port: {url}"))?;
    let port: u16 = port_text
        .parse()
        .map_err(|_| format!("invalid port in URL: {url}"))?;
    let mut stream =
        TcpStream::connect((host, port)).map_err(|err| sanitize_error(err.to_string()))?;
    stream
        .set_read_timeout(Some(Duration::from_secs(8)))
        .map_err(|err| err.to_string())?;
    let payload = body.unwrap_or("");
    let request = format!(
        "{method} {path} HTTP/1.1\r\nHost: {host_port}\r\nConnection: close\r\nAccept: application/json,*/*\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n{payload}",
        payload.as_bytes().len()
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|err| sanitize_error(err.to_string()))?;
    let mut response = Vec::new();
    stream
        .read_to_end(&mut response)
        .map_err(|err| sanitize_error(err.to_string()))?;
    parse_http_response(&response)
}

fn parse_http_response(response: &[u8]) -> Result<Vec<u8>, String> {
    let marker = b"\r\n\r\n";
    let header_end = response
        .windows(marker.len())
        .position(|window| window == marker)
        .ok_or_else(|| "invalid HTTP response".to_string())?;
    let header = String::from_utf8_lossy(&response[..header_end]);
    let status = header
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|code| code.parse::<u16>().ok())
        .ok_or_else(|| "invalid HTTP status line".to_string())?;
    let body = &response[header_end + marker.len()..];
    let chunked = header.lines().any(|line| {
        let lower = line.to_ascii_lowercase();
        lower.starts_with("transfer-encoding:") && lower.contains("chunked")
    });
    let body = if chunked {
        decode_chunked_body(body)?
    } else {
        body.to_vec()
    };
    if (200..300).contains(&status) {
        return Ok(body);
    }
    Err(format!(
        "HTTP {status}: {}",
        sanitize_error(String::from_utf8_lossy(&body).to_string())
    ))
}

fn decode_chunked_body(body: &[u8]) -> Result<Vec<u8>, String> {
    let mut index = 0;
    let mut decoded = Vec::new();
    while index < body.len() {
        let Some(size_line_end) = find_crlf(&body[index..]) else {
            return Err("invalid chunked response: missing chunk size terminator".to_string());
        };
        let size_line = &body[index..index + size_line_end];
        let size_text = String::from_utf8_lossy(size_line);
        let size_hex = size_text.split(';').next().unwrap_or("").trim();
        let size = usize::from_str_radix(size_hex, 16)
            .map_err(|_| "invalid chunked response: bad chunk size".to_string())?;
        index += size_line_end + 2;
        if size == 0 {
            return Ok(decoded);
        }
        if index + size > body.len() {
            return Err("invalid chunked response: chunk exceeds body length".to_string());
        }
        decoded.extend_from_slice(&body[index..index + size]);
        index += size;
        if body.get(index..index + 2) != Some(b"\r\n") {
            return Err("invalid chunked response: missing chunk terminator".to_string());
        }
        index += 2;
    }
    Err("invalid chunked response: missing final chunk".to_string())
}

fn find_crlf(value: &[u8]) -> Option<usize> {
    value.windows(2).position(|window| window == b"\r\n")
}

fn ensure_extension(path: PathBuf, format: &str) -> PathBuf {
    if path.extension().is_some() {
        return path;
    }
    let extension = if format == "docx" { "docx" } else { "md" };
    path.with_extension(extension)
}

fn dialog_path_to_pathbuf(file_path: tauri_plugin_dialog::FilePath) -> Result<PathBuf, String> {
    file_path
        .into_path()
        .map_err(|err| sanitize_error(err.to_string()))
}

fn mime_type_for_draft_kind(kind: &str) -> &'static str {
    if kind == "docx" {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    } else {
        "text/markdown"
    }
}

fn ensure_config_is_redacted(value: &mut Value) -> Result<(), String> {
    if value.get("api_key").is_some() {
        return Err("desktop config response exposed raw api_key".to_string());
    }
    if let Some(object) = value.as_object_mut() {
        for field in REDACTED_CONFIG_FIELDS {
            object.entry(*field).or_insert(Value::Null);
        }
    }
    Ok(())
}

fn sanitize_error(value: String) -> String {
    value
        .replace(SECRET_PREFIX, SECRET_REDACTION)
        .chars()
        .take(512)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn allocates_localhost_port() {
        let port = find_available_port().expect("port");
        assert!(port > 0);
    }

    #[test]
    fn appends_expected_export_extension() {
        assert_eq!(
            ensure_extension(PathBuf::from("/tmp/patent"), "docx"),
            PathBuf::from("/tmp/patent.docx")
        );
        assert_eq!(
            ensure_extension(PathBuf::from("/tmp/patent"), "sidecar"),
            PathBuf::from("/tmp/patent.md")
        );
    }

    #[test]
    fn preserves_existing_export_extension() {
        assert_eq!(
            ensure_extension(PathBuf::from("/tmp/patent.custom"), "docx"),
            PathBuf::from("/tmp/patent.custom")
        );
    }

    #[test]
    fn decodes_chunked_http_response_body() {
        let response =
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\nB\r\n{\"ok\":true}\r\n0\r\n\r\n";
        assert_eq!(
            parse_http_response(response).expect("response"),
            b"{\"ok\":true}"
        );
    }

    #[test]
    fn rejects_malformed_chunked_http_response_body() {
        let response = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\nB\r\n{\"ok\":true}";
        assert!(parse_http_response(response).is_err());
    }
}
