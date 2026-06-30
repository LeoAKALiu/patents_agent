"""PR 审核器 —— 关联校验 + 代码审核 + 状态监控。"""
import re
import requests
from typing import TypedDict
from github_client import get_client, GitHubClient
from config import LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL
from utils import logger, retry


class Verdict(TypedDict):
    issue_number: int
    pr_number: int | None
    status: str  # CONFIRMED | PARTIAL | MISMATCH | NO_PR | WAITING
    detail: str


# Matches GitHub-supported closing keywords with optional full URL prefix.
# Uses \b word boundary to avoid matching inside words like "disclosure".
_FIXES_PATTERN = r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+(?:https://github\.com/\S+/issues/)?#(\d+)"


def _find_fixes_keywords(body: str) -> list[int]:
    """从 PR body 中提取 Fixes #N / Closes #N 的 issue 号。"""
    return [int(n) for n in re.findall(_FIXES_PATTERN, body, re.IGNORECASE)]


# ── ① 关联校验 ──

def link_check(client: GitHubClient | None = None) -> list[Verdict]:
    """检查 open issue 是否有关联 PR 及 Fixes #N 关键字。"""
    if client is None:
        client = get_client()

    issues = client.list_issues(state="open")
    prs = client.list_prs(state="open")
    logger.info("关联校验: %s 个 open issues, %s 个 open PRs", len(issues), len(prs))

    # 构建 issue → PR 映射 (from PR body)
    issue_pr_map: dict[int, list[int]] = {}
    for pr in prs:
        linked = _find_fixes_keywords(pr.get("body", ""))
        for n in linked:
            issue_pr_map.setdefault(n, []).append(pr["number"])

    results: list[Verdict] = []
    for issue in issues:
        i_num = issue["number"]
        linked_prs = issue_pr_map.get(i_num, [])

        if not linked_prs:
            results.append({
                "issue_number": i_num,
                "pr_number": None,
                "status": "NO_PR",
                "detail": f"Issue #{i_num} 没有关联的 PR，等待修复",
            })
            logger.info("Issue #%s: 无关联 PR", i_num)
        else:
            for pr_num in linked_prs:
                results.append({
                    "issue_number": i_num,
                    "pr_number": pr_num,
                    "status": "CONFIRMED",
                    "detail": f"Issue #{i_num} ← PR #{pr_num}（含 closing 关键字）",
                })

    return results


# ── ② 代码级审核 ──

def _build_review_prompt(issue_title: str, issue_body: str, diff: str) -> str:
    """构建 LLM 代码审核提示词。"""
    body_truncated = issue_body[:3000]
    diff_truncated = diff[:8000]
    body_suffix = "\n...[内容已截断]" if len(issue_body) > 3000 else ""
    diff_suffix = "\n...[内容已截断]" if len(diff) > 8000 else ""
    return f"""你是一个代码审核专家。请判断 PR 的改动是否真正解决了 issue 描述的问题。

## Issue
标题：{issue_title}
描述：
{body_truncated}{body_suffix}

## PR Diff
```diff
{diff_truncated}{diff_suffix}
```

请判断代码变更是否解决了 issue。回答仅包含以下三个词之一：
- CONFIRMED：变更完全解决了问题
- PARTIAL：变更解决了部分问题，但还有遗漏
- MISMATCH：变更与问题描述不匹配

然后一行简短说明原因。格式："结论\\n原因" """


@retry(max_attempts=2, backoff=5.0)
def _call_llm_review(prompt: str) -> tuple[str, str]:
    """调用 LLM 审核 PR diff。返回 (结论, 原因)。"""
    if not LLM_API_KEY:
        return ("WAITING", "LLM 未配置，跳过代码审核")

    if LLM_PROVIDER == "anthropic":
        return _review_anthropic(prompt)
    elif LLM_PROVIDER in ("openai", "openai-compatible"):
        return _review_openai(prompt)
    else:
        return ("WAITING", f"未知 LLM_PROVIDER: {LLM_PROVIDER}")


def _parse_llm_verdict(text: str) -> tuple[str, str]:
    """从 LLM 响应中提取并验证裁决结论和原因。"""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if len(lines) > 2 and lines[-1].strip() == "```" else lines[1:])
        text = text.strip()
    parts = text.split("\n", 1)
    raw_verdict = parts[0].strip().upper().rstrip(".")
    reason = parts[1].strip() if len(parts) > 1 else ""
    # Normalize known variants
    VALID = {"CONFIRMED", "PARTIAL", "MISMATCH"}
    known_map = {
        "CONFIRM": "CONFIRMED", "YES": "CONFIRMED", "APPROVED": "CONFIRMED",
        "MISMATCHED": "MISMATCH", "REJECTED": "MISMATCH",
        "PARTIALLY": "PARTIAL",
    }
    verdict = known_map.get(raw_verdict, raw_verdict)
    if verdict not in VALID:
        if not reason:
            reason = f"无法解析 LLM 输出: {raw_verdict}"
        return ("WAITING", reason)
    return (verdict, reason)


def _review_anthropic(prompt: str) -> tuple[str, str]:
    """调用 Anthropic Messages API 审核。"""
    if not LLM_API_KEY:
        return ("WAITING", "LLM_API_KEY 未设置")
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": LLM_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "max_tokens": 512,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["content"][0]["text"]
    return _parse_llm_verdict(text)


def _review_openai(prompt: str) -> tuple[str, str]:
    """调用 OpenAI / OpenAI 兼容 API 审核。"""
    if not LLM_API_KEY:
        return ("WAITING", "LLM_API_KEY 未设置")
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
            "max_tokens": 512,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return _parse_llm_verdict(text)


def code_review(client: GitHubClient | None = None) -> list[Verdict]:
    """对每个关联 PR 的 issue 做代码级审核。"""
    if client is None:
        client = get_client()

    issues = client.list_issues(state="open")
    prs = client.list_prs(state="open")
    results: list[Verdict] = []

    for issue in issues:
        i_num = issue["number"]
        linked_prs = []
        for pr in prs:
            linked = _find_fixes_keywords(pr.get("body", ""))
            if i_num in linked:
                linked_prs.append(pr)

        if not linked_prs:
            continue

        for pr in linked_prs:
            pr_num = pr["number"]
            try:
                diff = client.get_pr_diff(pr_num)
                verdict, reason = _call_llm_review(
                    _build_review_prompt(issue["title"], issue.get("body", ""), diff)
                )
            except Exception as e:
                verdict, reason = "WAITING", f"审核失败: {e}"

            logger.info("Issue #%s ← PR #%s: %s — %s", i_num, pr_num, verdict, reason)
            results.append({
                "issue_number": i_num,
                "pr_number": pr_num,
                "status": verdict,
                "detail": reason,
            })

            # 对 PARTIAL / MISMATCH 评论
            if verdict in ("PARTIAL", "MISMATCH"):
                comment = (
                    f"## 代码审核结果: {verdict}\n\n"
                    f"{reason}\n\n"
                    f"> 此评论由 AI 自动审核系统生成。"
                )
                try:
                    client.add_pr_comment(pr_num, comment)
                except Exception as e:
                    logger.warning("评论 PR #%s 失败: %s", pr_num, e)

    return results


# ── ③ 状态监控 ──

def status_monitor(client: GitHubClient | None = None) -> list[Verdict]:
    """监控 open issue 关联 PR 的状态。"""
    if client is None:
        client = get_client()

    issues = client.list_issues(state="open")
    all_prs = client.list_prs(state="all")  # 包括已合并/已关闭
    results: list[Verdict] = []

    for issue in issues:
        i_num = issue["number"]
        linked_prs = []
        for pr in all_prs:
            linked = _find_fixes_keywords(pr.get("body", ""))
            if i_num in linked:
                linked_prs.append(pr)

        if not linked_prs:
            continue

        for pr in linked_prs:
            pr_num = pr["number"]
            merged = pr.get("merged_at") is not None
            pr_state = pr.get("state", "unknown")

            if merged:
                status = "CONFIRMED"
                detail = f"PR #{pr_num} 已合并 → Issue #{i_num} 应已自动关闭"
                # 如果 issue 还未关闭，手动关闭
                if issue["state"] == "open":
                    try:
                        client.close_issue(i_num)
                        logger.info("已手动关闭 issue #%s", i_num)
                    except Exception as e:
                        logger.warning("关闭 issue #%s 失败: %s", i_num, e)
            elif pr_state == "closed" and not merged:
                status = "MISMATCH"
                detail = f"PR #{pr_num} 已关闭但未合并 → Issue #{i_num} 仍未修复"
            else:
                status = "WAITING"
                detail = f"PR #{pr_num} 仍在 open 状态"

            logger.info("Issue #%s ← PR #%s: %s — %s", i_num, pr_num, status, detail)
            results.append({
                "issue_number": i_num,
                "pr_number": pr_num,
                "status": status,
                "detail": detail,
            })

    return results


# ── 主入口 ──

def verify() -> dict[str, list[Verdict]]:
    """运行全部三种审核，返回汇总。"""
    client = get_client()
    logger.info("=" * 50)
    logger.info("开始 PR 审核流程")

    logger.info(">>> ① 关联校验")
    link_results = link_check(client)

    logger.info(">>> ② 代码级审核")
    review_results = code_review(client)

    logger.info(">>> ③ 状态监控")
    status_results = status_monitor(client)

    all_results = {
        "link_check": link_results,
        "code_review": review_results,
        "status_monitor": status_results,
    }

    total = sum(len(v) for v in all_results.values())
    confirmed = sum(
        1 for vlist in all_results.values() for v in vlist if v["status"] == "CONFIRMED"
    )
    logger.info("审核完成: %s 条校验, %s 条已确认", total, confirmed)
    logger.info("=" * 50)

    return all_results
