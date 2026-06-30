"""GitHub REST API 客户端 —— 所有 API 调用通过此模块。"""
import base64
import re
import requests
from typing import Any
from config import GITHUB_TOKEN, GITHUB_API_BASE, REPO_OWNER, REPO_NAME
from utils import retry, logger, hash_title


class GitHubClient:
    """GitHub REST API 客户端。"""

    def __init__(self, timeout: int = 30) -> None:
        self.base = GITHUB_API_BASE
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.repo_path = f"/repos/{REPO_OWNER}/{REPO_NAME}"

    def _get(self, endpoint: str, params: dict | None = None) -> dict | list:
        """GET 请求。"""
        url = f"{self.base}{endpoint}"
        resp = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, body: dict) -> dict:
        """POST 请求。"""
        url = f"{self.base}{endpoint}"
        resp = requests.post(url, headers=self.headers, json=body, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, endpoint: str, body: dict) -> dict:
        """PATCH 请求。"""
        url = f"{self.base}{endpoint}"
        resp = requests.patch(url, headers=self.headers, json=body, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _get_all_pages(self, endpoint: str, params: dict | None = None, max_pages: int = 20) -> list[dict]:
        """GET 请求，自动遍历所有分页，返回聚合结果。

        max_pages 防止死循环（GitHub Contents API 等端点不支持 page 分页参数）。"""
        all_items: list[dict] = []
        if params is None:
            params = {}
        params.setdefault("per_page", 100)
        page = 1
        prev_len = -1
        while page <= max_pages:
            params["page"] = page
            data = self._get(endpoint, dict(params))
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "items" in data:
                items = data["items"]
            else:
                break
            if not items:
                break
            # 检测重复返回（Contents API 不支持 page，每页返回相同数据）
            if len(items) == prev_len and len(items) == len(all_items[-prev_len:]) if prev_len > 0 else False:
                break
            all_items.extend(items)
            if len(items) < int(params.get("per_page", 100)):
                break
            prev_len = len(items)
            page += 1
        return all_items

    # ── 文件操作 ──

    @retry(max_attempts=3, backoff=2.0)
    def get_file(self, path: str, ref: str = "main") -> str:
        """获取文件内容（Base64 解码后的纯文本）。"""
        endpoint = f"{self.repo_path}/contents/{path}"
        data = self._get(endpoint, {"ref": ref})
        return base64.b64decode(data["content"]).decode("utf-8")

    @retry(max_attempts=3, backoff=2.0)
    def list_files(self, directory: str = "", ref: str = "main") -> list[dict]:
        """列出目录内容（自动翻页）。"""
        endpoint = f"{self.repo_path}/contents/{directory}"
        items = self._get_all_pages(endpoint, {"ref": ref})
        if not isinstance(items, list):
            return []
        return items

    # ── Issue 操作 ──

    @retry(max_attempts=3, backoff=2.0)
    def create_issue(self, title: str, body: str, labels: list[str]) -> dict:
        """创建单个 issue。"""
        endpoint = f"{self.repo_path}/issues"
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        return self._post(endpoint, payload)

    @retry(max_attempts=3, backoff=2.0)
    def list_issues(self, state: str = "open", labels: str = "") -> list[dict]:
        """列出所有 issues（自动翻页）。"""
        params: dict[str, str | int] = {"state": state, "per_page": 100}
        if labels:
            params["labels"] = labels
        result = self._get_all_pages(f"{self.repo_path}/issues", params)
        # 过滤掉 PR（GitHub 的 issues API 也返回 PR）
        return [i for i in result if "pull_request" not in i]

    @retry(max_attempts=3, backoff=2.0)
    def close_issue(self, issue_number: int) -> dict:
        """关闭 issue。"""
        endpoint = f"{self.repo_path}/issues/{issue_number}"
        return self._patch(endpoint, {"state": "closed"})

    def batch_create_issues(self, issues: list[dict]) -> dict:
        """批量创建 issues，基于 title hash 去重。

        返回 {"created": [...], "skipped": N, "failed": N, "errors": [...]}。
        """
        existing = self.list_issues(state="open")
        existing_hashes = {hash_title(i["title"]) for i in existing}

        created: list[dict] = []
        skipped = 0
        failed = 0
        errors: list[str] = []
        for issue in issues:
            title_hash = hash_title(issue["title"])
            if title_hash in existing_hashes:
                logger.info("跳过重复 issue: %s", issue["title"])
                skipped += 1
                continue
            try:
                result = self.create_issue(
                    title=issue["title"],
                    body=issue["body"],
                    labels=issue.get("labels", []),
                )
                created.append(result)
                existing_hashes.add(title_hash)
                logger.info("已创建 issue #%s: %s", result["number"], issue["title"])
            except Exception as e:
                failed += 1
                error_msg = f"{issue['title']}: {e}"
                errors.append(error_msg)
                logger.error("创建 issue 失败: %s", error_msg)

        logger.info("批量创建完成: %s 已创建, %s 已跳过, %s 失败", len(created), skipped, failed)
        return {"created": created, "skipped": skipped, "failed": failed, "errors": errors}

    # ── PR 操作 ──

    @retry(max_attempts=3, backoff=2.0)
    def list_prs(self, state: str = "open") -> list[dict]:
        """列出所有 PR（自动翻页）。"""
        params = {"state": state, "per_page": 100}
        return self._get_all_pages(f"{self.repo_path}/pulls", params)

    @retry(max_attempts=3, backoff=2.0)
    def get_pr(self, pr_number: int) -> dict:
        """获取 PR 详情。"""
        return self._get(f"{self.repo_path}/pulls/{pr_number}")

    @retry(max_attempts=3, backoff=2.0)
    def get_pr_diff(self, pr_number: int) -> str:
        """获取 PR 的 unified diff（纯文本）。"""
        url = f"{self.base}{self.repo_path}/pulls/{pr_number}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        resp = requests.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    @retry(max_attempts=3, backoff=2.0)
    def get_issues_linked_to_pr(self, pr_number: int) -> list[dict]:
        """获取 PR 关联的 closing issues。"""
        pr = self.get_pr(pr_number)
        body = pr.get("body", "")
        pattern = r"(?:fixes|closes|resolves)\s+#(\d+)"
        matches = re.findall(pattern, body, re.IGNORECASE)
        issues = []
        for num_str in matches:
            try:
                issue = self._get(f"{self.repo_path}/issues/{int(num_str)}")
                issues.append(issue)
            except Exception:
                continue
        return issues

    @retry(max_attempts=3, backoff=2.0)
    def add_pr_comment(self, pr_number: int, body: str) -> dict:
        """在 PR 下发表评论。"""
        return self._post(f"{self.repo_path}/issues/{pr_number}/comments", {"body": body})


# 模块级单例
_client: GitHubClient | None = None


def get_client() -> GitHubClient:
    global _client
    if _client is None:
        _client = GitHubClient()
    return _client
