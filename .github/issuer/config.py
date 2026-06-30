"""配置模块 —— 所有配置从环境变量读取，提供合理默认值。"""
import os
from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# 目标仓库
REPO_OWNER = _env("REPO_OWNER", "LeoAKALiu")
REPO_NAME = _env("REPO_NAME", "patents_agent")

# GitHub 认证
GITHUB_TOKEN = _env("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN 环境变量未设置")

# LLM 配置
LLM_PROVIDER = _env("LLM_PROVIDER", "anthropic")  # anthropic | openai | openai-compatible
LLM_API_KEY = _env("LLM_API_KEY", "")
LLM_MODEL = _env("LLM_MODEL", "claude-sonnet-4-6")
LLM_BASE_URL = _env("LLM_BASE_URL", "")  # openai-compatible 时使用

# 阈值
SEVERITY_THRESHOLD = _env("SEVERITY_THRESHOLD", "low")  # low | medium | high

def _env_int(key: str, default: int) -> int:
    """从环境变量读取整数，解析失败时给出明确错误信息。"""
    raw = os.environ.get(key, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"{key} 环境变量必须是整数，当前值: {raw}") from None


# loop 模式
LOOP_SLEEP_SECONDS = _env_int("LOOP_SLEEP_SECONDS", 3600)

# GitHub API
GITHUB_API_BASE = "https://api.github.com"
