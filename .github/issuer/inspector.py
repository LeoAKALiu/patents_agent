"""Issue 发现器 —— 静态规则 + LLM 分析。"""
import json
import re
import requests
from typing import TypedDict
from github_client import get_client
from config import LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL, SEVERITY_THRESHOLD, REPO_OWNER, REPO_NAME
from utils import logger, retry


class IssueDict(TypedDict):
    title: str
    body: str
    labels: list[str]
    severity: str  # low | medium | high


SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def rule_bare_except(path: str, content: str) -> IssueDict | None:
    """检测 bare except 子句。"""
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("except:"):
            return {
                "title": f"bare except in {path}:{i}",
                "body": (
                    f"## 问题描述\n"
                    f"文件中存在 bare `except:` 子句，会捕获所有异常（包括 KeyboardInterrupt），"
                    f"掩盖潜在错误。\n\n"
                    f"## 位置\n- 文件：`{path}`\n- 行号：{i}\n\n"
                    f"## 建议\n使用 `except Exception as e:` 明确捕获预期异常。"
                ),
                "labels": ["bug"],
                "severity": "medium",
            }
    return None


def rule_hardcoded_secret(path: str, content: str) -> list[IssueDict]:
    """检测硬编码的 API key / token / password。"""
    patterns = [
        (r'(?:api[_-]?key|apikey)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}["\']', "API Key"),
        (r'(?:password|passwd)\s*[:=]\s*["\'][^"\']+["\']', "Password"),
        (r'ghp_[A-Za-z0-9]{36}', "GitHub Token"),
        (r'sk-[A-Za-z0-9]{32,}', "OpenAI Key"),
        (r'sk-ant-[A-Za-z0-9\-_]{32,}', "Anthropic Key"),
    ]
    issues: list[IssueDict] = []
    seen_kinds: set[str] = set()
    for pat, kind in patterns:
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            line_no = content[:m.start()].count("\n") + 1
            seen_kinds.add(kind)
            issues.append({
                "title": f"hardcoded {kind} in {path}:{line_no}",
                "body": (
                    f"## 问题描述\n"
                    f"代码中检测到硬编码的 **{kind}**，存在安全风险。\n\n"
                    f"## 位置\n- 文件：`{path}`\n- 行号：{line_no}\n\n"
                    f"## 建议\n使用环境变量或密钥管理服务替代。"
                ),
                "labels": ["security"],
                "severity": "high",
            })
    return issues if issues else None


def rule_empty_error_handler(path: str, content: str) -> IssueDict | None:
    """检测 `except: pass` 或 `except Exception: pass`。"""
    pattern = r'except\s*(Exception)?\s*:\s*\n\s*pass\b'
    for m in re.finditer(pattern, content):
        line_no = content[:m.start()].count("\n") + 1
        return {
            "title": f"empty error handler in {path}:{line_no}",
            "body": (
                f"## 问题描述\n"
                f"`except: pass` 静默吞下所有异常，导致错误不可见，调试困难。\n\n"
                f"## 位置\n- 文件：`{path}`\n- 行号：{line_no}\n\n"
                f"## 建议\n至少记录日志：`except Exception as e: logger.error(...)`"
            ),
            "labels": ["bug"],
            "severity": "medium",
        }
    return None


def rule_todo_fixme(path: str, content: str) -> list[IssueDict]:
    """检测 TODO/FIXME/HACK 标记。"""
    issues: list[IssueDict] = []
    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        for marker in ["TODO", "FIXME", "HACK", "XXX"]:
            if f"# {marker}" in stripped:
                issues.append({
                    "title": f"{marker} in {path}:{i}",
                    "body": (
                        f"## 问题描述\n"
                        f"发现 `{marker}` 标记。\n\n"
                        f"## 位置\n- 文件：`{path}`\n- 行号：{i}\n"
                        f"## 代码\n```\n{stripped}\n```"
                    ),
                    "labels": ["tech-debt"],
                    "severity": "low",
                })
    return issues


def rule_broad_import(path: str, content: str) -> IssueDict | None:
    """检测 `from module import *`。"""
    m = re.search(r'from\s+\S+\s+import\s+\*', content)
    if m:
        line_no = content[:m.start()].count("\n") + 1
        return {
            "title": f"wildcard import in {path}:{line_no}",
            "body": (
                f"## 问题描述\n"
                f"`from ... import *` 导入所有公共名称，污染命名空间，导致意外的名称冲突。\n\n"
                f"## 位置\n- 文件：`{path}`\n- 行号：{line_no}\n\n"
                f"## 建议\n显式导入需要的名称，或使用 `__all__` 控制导出。"
            ),
            "labels": ["code-quality"],
            "severity": "low",
        }
    return None


STATIC_RULES = [
    rule_bare_except,
    rule_hardcoded_secret,
    rule_empty_error_handler,
    rule_todo_fixme,
    rule_broad_import,
]


def run_static_rules(path: str, content: str) -> list[IssueDict]:
    """对所有静态规则运行文件内容，返回发现的问题。"""
    results: list[IssueDict] = []
    for rule in STATIC_RULES:
        try:
            result = rule(path, content)
            if result is None:
                continue
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)
        except Exception as e:
            logger.warning("规则 %s 在 %s 上失败: %s", rule.__name__, path, e)
    return results


# ── LLM 分析 ──

def _build_llm_prompt(path: str, content: str) -> str:
    """构建 LLM 分析提示词。"""
    return f"""分析以下代码文件，发现潜在的 bug、安全漏洞、代码质量问题或维护性问题。

文件：{path}
（文件总长度：{len(content)} 字符{f'，以下仅显示前 8000 字符' if len(content) > 8000 else ''}）

```python
{content[:8000]}
```

请以 JSON 数组格式返回发现的问题，每个问题包含 title, body, severity (low/medium/high), labels。
如果没有发现问题，返回空数组 []。

title 格式："<问题简述> in {path}:<行号>"
body 格式：Markdown，包含 ## 问题描述、## 位置、## 影响、## 建议
labels 从以下选择：["bug", "security", "code-quality", "performance", "tech-debt"]

只返回 JSON，不要其他文字。"""


@retry(max_attempts=2, backoff=5.0)
def _call_llm(prompt: str) -> list[IssueDict]:
    """调用 LLM 分析代码。支持 Anthropic / OpenAI / OpenAI 兼容。"""
    if LLM_PROVIDER == "anthropic":
        return _call_anthropic(prompt)
    elif LLM_PROVIDER in ("openai", "openai-compatible"):
        return _call_openai(prompt)
    else:
        logger.warning("未知 LLM_PROVIDER: %s，跳过 LLM 分析", LLM_PROVIDER)
        return []


def _call_anthropic(prompt: str) -> list[IssueDict]:
    """调用 Anthropic Messages API。"""
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY 未设置，无法调用 Anthropic API")
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": LLM_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["content"][0]["text"]
    return _parse_llm_response(text)


def _call_openai(prompt: str) -> list[IssueDict]:
    """调用 OpenAI / OpenAI 兼容 API。"""
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY 未设置，无法调用 OpenAI API")
    url = LLM_BASE_URL or "https://api.openai.com/v1"
    url = f"{url.rstrip('/')}/chat/completions"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return _parse_llm_response(text)


def _parse_llm_response(text: str) -> list[IssueDict]:
    """从 LLM 响应文本中提取 JSON 数组。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(text)
        if isinstance(data, list):
            valid: list[IssueDict] = []
            for item in data:
                if isinstance(item, dict) and "title" in item and "body" in item:
                    item.setdefault("severity", "medium")
                    item.setdefault("labels", [])
                    valid.append(item)
            return valid
    except json.JSONDecodeError:
        logger.warning("LLM 响应 JSON 解析失败，原始内容: %s...", text[:200])
    return []


# ── 主入口 ──

def discover() -> list[IssueDict]:
    """扫描目标仓库，发现并返回结构化 issues。"""
    client = get_client()
    all_issues: list[IssueDict] = []

    logger.info("开始扫描仓库 %s/%s...", REPO_OWNER, REPO_NAME)

    python_files = _find_python_files(client)
    logger.info("找到 %s 个 Python 文件", len(python_files))

    for path in python_files:
        try:
            content = client.get_file(path)
        except Exception as e:
            logger.warning("获取文件 %s 失败: %s", path, e)
            continue

        static_issues = run_static_rules(path, content)
        all_issues.extend(static_issues)

        if LLM_API_KEY and (static_issues or len(content.split("\n")) > 100):
            try:
                llm_issues = _call_llm(_build_llm_prompt(path, content))
                all_issues.extend(llm_issues)
            except Exception as e:
                logger.warning("LLM 分析文件 %s 失败: %s", path, e)

    threshold = SEVERITY_ORDER.get(SEVERITY_THRESHOLD, 0)
    filtered = [i for i in all_issues if SEVERITY_ORDER.get(i.get("severity", "low"), 0) >= threshold]
    filtered.sort(key=lambda i: SEVERITY_ORDER.get(i.get("severity", "low"), 0), reverse=True)

    logger.info("发现 %s 个 issues（过滤后: %s）", len(all_issues), len(filtered))
    return filtered


def _find_python_files(client: "GitHubClient", directory: str = "") -> list[str]:
    """递归查找仓库中的 Python 文件。"""
    files: list[str] = []
    try:
        items = client.list_files(directory)
    except Exception:
        return files
    for item in items:
        if item["type"] == "file" and item["name"].endswith(".py"):
            files.append(item["path"])
        elif item["type"] == "dir":
            files.extend(_find_python_files(client, item["path"]))
    return files
