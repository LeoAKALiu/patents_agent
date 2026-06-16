use base64::{engine::general_purpose, Engine as _};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    fs::{self, OpenOptions},
    io::{Read, Write},
    net::{TcpListener, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    thread,
    time::{Duration, Instant},
};
use tauri::webview::PageLoadEvent;
use tauri::{AppHandle, Manager, State};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_opener::OpenerExt;

const HEALTH_PATH: &str = "/api/health";
const STARTUP_TIMEOUT_MS: u64 = 20_000;
const DOM_SMOKE_TIMEOUT_MS: u64 = 15_000;
const DOM_SMOKE_PROBE_ATTEMPTS: usize = 20;
const DOM_SMOKE_PROBE_INTERVAL_MS: u64 = 500;
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
    let dom_smoke_done = Arc::new(AtomicBool::new(false));
    let dom_smoke_done_for_setup = Arc::clone(&dom_smoke_done);
    let dom_smoke_done_for_page = Arc::clone(&dom_smoke_done);
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(BackendState::default())
        .setup(move |app| {
            let data_dir = app.path().app_data_dir().unwrap_or_else(|_| {
                std::env::temp_dir()
                    .join("PatentAgent")
                    .join("backend-data")
            });
            fs::create_dir_all(&data_dir)?;
            append_backend_startup_log(&data_dir, "setup: begin");
            match backend_root(app.handle()).and_then(|repo_root| {
                append_backend_startup_log(
                    &data_dir,
                    &format!("backend root: {}", repo_root.display()),
                );
                start_backend(&repo_root, &data_dir).map_err(|err| err.to_string())
            }) {
                Ok(supervisor) => {
                    append_backend_startup_log(
                        &data_dir,
                        &format!("backend ready: {}", supervisor.info.health_url),
                    );
                    let state = app.state::<BackendState>();
                    *state
                        .supervisor
                        .lock()
                        .map_err(|_| "backend state lock poisoned")? = Some(supervisor);
                }
                Err(err) => {
                    append_backend_startup_log(&data_dir, &format!("backend failed: {err}"));
                    write_backend_startup_error(&data_dir, &err);
                    eprintln!("PatentAgent backend startup failed: {err}");
                }
            }
            if dom_smoke_enabled() {
                start_dom_smoke_timeout(
                    app.handle().clone(),
                    Arc::clone(&dom_smoke_done_for_setup),
                );
            }
            Ok(())
        })
        .on_page_load(move |webview, payload| {
            if dom_smoke_enabled() && payload.event() == PageLoadEvent::Finished {
                run_renderer_dom_smoke(webview, Arc::clone(&dom_smoke_done_for_page));
            }
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

fn dom_smoke_enabled() -> bool {
    std::env::var_os("PATENTAGENT_TAURI_DOM_SMOKE").is_some()
}

fn dom_smoke_report_path() -> Option<PathBuf> {
    std::env::var_os("PATENTAGENT_TAURI_DOM_SMOKE_REPORT").map(PathBuf::from)
}

fn start_dom_smoke_timeout(app_handle: AppHandle, done: Arc<AtomicBool>) {
    thread::spawn(move || {
        thread::sleep(Duration::from_millis(DOM_SMOKE_TIMEOUT_MS));
        if done.swap(true, Ordering::SeqCst) {
            return;
        }
        let report = json!({
            "ok": false,
            "error": "renderer DOM smoke timed out",
        });
        write_dom_smoke_report(&report);
        eprintln!("TAURI_DOM_SMOKE {}", report);
        shutdown_backend(&app_handle);
        app_handle.exit(4);
    });
}

fn run_renderer_dom_smoke(webview: &tauri::Webview, done: Arc<AtomicBool>) {
    let webview = webview.clone();
    let app_handle = webview.app_handle().clone();
    thread::spawn(move || {
        for attempt in 0..DOM_SMOKE_PROBE_ATTEMPTS {
            thread::sleep(Duration::from_millis(DOM_SMOKE_PROBE_INTERVAL_MS));
            if done.load(Ordering::SeqCst) {
                return;
            }
            let webview_for_probe = webview.clone();
            let app_handle_for_probe = app_handle.clone();
            let done_for_probe = Arc::clone(&done);
            let is_final_attempt = attempt + 1 == DOM_SMOKE_PROBE_ATTEMPTS;
            if let Err(err) = app_handle.run_on_main_thread(move || {
                run_renderer_dom_smoke_probe(
                    &webview_for_probe,
                    app_handle_for_probe,
                    done_for_probe,
                    is_final_attempt,
                );
            }) {
                if done.swap(true, Ordering::SeqCst) {
                    return;
                }
                let report = json!({
                    "ok": false,
                    "error": format!("renderer DOM smoke scheduling failed: {err}"),
                });
                write_dom_smoke_report(&report);
                eprintln!("TAURI_DOM_SMOKE {}", report);
                shutdown_backend(&app_handle);
                app_handle.exit(3);
                return;
            }
        }
    });
}

fn run_renderer_dom_smoke_probe(
    webview: &tauri::Webview,
    app_handle: AppHandle,
    done: Arc<AtomicBool>,
    is_final_attempt: bool,
) {
    let script = r#"
(() => {
  const root = document.getElementById("root");
  const text = (document.body && document.body.innerText || "").replace(/\s+/g, " ").trim();
  const result = {
    url: window.location.href,
    readyState: document.readyState,
    title: document.title,
    rootChildren: root ? root.children.length : 0,
    hasAppShell: Boolean(document.querySelector(".app-shell")),
    hasSidebar: Boolean(document.querySelector(".sidebar")),
    hasTopbar: Boolean(document.querySelector(".topbar")),
    hasErrorPage: text.includes("应用启动失败") || text.includes("React 根节点没有产生"),
    textSample: text.slice(0, 240)
  };
  result.ok = result.rootChildren > 0 &&
    result.hasAppShell &&
    result.hasSidebar &&
    result.hasTopbar &&
    !result.hasErrorPage;
    return result;
})()
"#;
    let app_handle_for_callback = app_handle.clone();
    let done_for_callback = Arc::clone(&done);
    let eval_result = webview.eval_with_callback(script, move |result| {
        let parsed = serde_json::from_str::<Value>(&result).unwrap_or_else(|err| {
            json!({
                "ok": false,
                "error": format!("renderer DOM smoke returned invalid JSON: {err}"),
                "raw": result,
            })
        });
        let ok = parsed.get("ok").and_then(Value::as_bool).unwrap_or(false);
        if !ok && !is_final_attempt {
            return;
        }
        if done_for_callback.swap(true, Ordering::SeqCst) {
            return;
        }
        write_dom_smoke_report(&parsed);
        println!("TAURI_DOM_SMOKE {}", parsed);
        shutdown_backend(&app_handle_for_callback);
        app_handle_for_callback.exit(if ok { 0 } else { 2 });
    });
    if let Err(err) = eval_result {
        if done.swap(true, Ordering::SeqCst) {
            return;
        }
        let report = json!({
            "ok": false,
            "error": format!("renderer DOM smoke eval failed: {err}"),
        });
        write_dom_smoke_report(&report);
        eprintln!("TAURI_DOM_SMOKE {}", report);
        shutdown_backend(&app_handle);
        app_handle.exit(3);
    }
}

fn write_dom_smoke_report(report: &Value) {
    if let Some(path) = dom_smoke_report_path() {
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        if let Ok(text) = serde_json::to_string_pretty(report) {
            let _ = fs::write(path, text);
        }
    }
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

fn backend_root(app_handle: &AppHandle) -> Result<PathBuf, String> {
    if let Some(path) = std::env::var_os("PATENTAGENT_REPO_ROOT").map(PathBuf::from) {
        return ensure_backend_root(path);
    }

    if let Ok(resource_dir) = app_handle.path().resource_dir() {
        if is_backend_root(&resource_dir) {
            return Ok(resource_dir);
        }
    }

    let dev_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or("CARGO_MANIFEST_DIR has no parent")?
        .to_path_buf();
    ensure_backend_root(dev_root)
}

fn ensure_backend_root(path: PathBuf) -> Result<PathBuf, String> {
    if is_backend_root(&path) {
        Ok(path)
    } else {
        Err(format!(
            "{} does not contain backend/app/main.py",
            path.display()
        ))
    }
}

fn is_backend_root(path: &Path) -> bool {
    path.join("backend").join("app").join("main.py").is_file()
}

fn start_backend(
    repo_root: &Path,
    data_dir: &Path,
) -> Result<BackendSupervisor, Box<dyn std::error::Error>> {
    let mut errors = Vec::new();
    for python in python_candidates() {
        append_backend_startup_log(data_dir, &format!("trying python: {python}"));
        match start_backend_with_python(&python, repo_root, data_dir) {
            Ok(supervisor) => return Ok(supervisor),
            Err(err) => {
                append_backend_startup_log(data_dir, &format!("python failed: {python}: {err}"));
                errors.push(format!("{python}: {err}"));
            }
        }
    }
    Err(format!(
        "backend did not start with any Python interpreter: {}",
        errors.join(" | ")
    )
    .into())
}

fn python_candidates() -> Vec<String> {
    let mut candidates = Vec::new();
    if let Ok(python) = std::env::var("PATENTAGENT_PYTHON") {
        push_unique(&mut candidates, python);
    }
    for python in [
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
        "/usr/local/bin/python3",
        "/opt/homebrew/bin/python3",
        "/opt/homebrew/bin/python3.12",
        "python3",
    ] {
        push_unique(&mut candidates, python.to_string());
    }
    candidates
}

fn push_unique(values: &mut Vec<String>, value: String) {
    if !values.iter().any(|existing| existing == &value) {
        values.push(value);
    }
}

fn start_backend_with_python(
    python: &str,
    repo_root: &Path,
    data_dir: &Path,
) -> Result<BackendSupervisor, Box<dyn std::error::Error>> {
    let port = find_available_port()?;
    let base_url = format!("http://127.0.0.1:{port}");
    let health_url = format!("{base_url}{HEALTH_PATH}");
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
        let stdout = read_child_pipe(&mut child.stdout);
        let stderr = read_child_pipe(&mut child.stderr);
        return Err(format!(
            "{err}; backend stdout: {}; backend stderr: {}",
            summarize_process_output(&stdout),
            summarize_process_output(&stderr)
        )
        .into());
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

fn write_backend_startup_error(data_dir: &Path, error: &str) {
    let path = data_dir.join("backend-startup-error.txt");
    let _ = fs::write(path, error);
}

fn append_backend_startup_log(data_dir: &Path, message: &str) {
    for path in [
        data_dir.join("backend-startup.log"),
        std::env::temp_dir().join("patentagent-tauri-startup.log"),
    ] {
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
            let _ = writeln!(file, "{message}");
        }
    }
}

fn read_child_pipe<R: Read>(pipe: &mut Option<R>) -> String {
    let mut output = String::new();
    if let Some(reader) = pipe.as_mut() {
        let _ = reader.read_to_string(&mut output);
    }
    output
}

fn summarize_process_output(output: &str) -> String {
    let trimmed = output.trim();
    if trimmed.is_empty() {
        return "<empty>".to_string();
    }
    const MAX_LEN: usize = 2_000;
    if trimmed.len() > MAX_LEN {
        format!("{}...[truncated]", &trimmed[..MAX_LEN])
    } else {
        trimmed.to_string()
    }
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
