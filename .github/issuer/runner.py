"""CLI 入口 —— discover | verify | loop 三种模式。"""
import sys
import time


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python runner.py <discover|verify|loop>")
        sys.exit(1)

    mode = sys.argv[1]

    if mode not in ("discover", "verify", "loop"):
        print(f"未知模式: {mode}。可选: discover | verify | loop")
        sys.exit(1)

    from utils import setup_logging
    setup_logging(verbose=True)

    if mode == "discover":
        _cmd_discover()
    elif mode == "verify":
        _cmd_verify()
    elif mode == "loop":
        _cmd_loop()


def _cmd_discover() -> None:
    """运行 inspector，生成 issues，推送 GitHub。"""
    from inspector import discover
    from github_client import get_client
    from utils import logger

    issues = discover()
    if not issues:
        logger.info("未发现新 issue，跳过推送")
        return

    client = get_client()
    result = client.batch_create_issues(issues)
    logger.info("discover 完成: %s 个 issue 已推送到 GitHub, %s 跳过, %s 失败",
                len(result["created"]), result["skipped"], result["failed"])


def _cmd_verify() -> None:
    """运行 verifier 全部三种审核。"""
    from verifier import verify

    results = verify()
    link = results["link_check"]
    review = results["code_review"]
    monitor = results["status_monitor"]

    # 输出摘要
    print("\n===== 审核摘要 =====")
    print(f"关联校验: {len(link)} 条")
    for r in link:
        print(f"  [{r['status']}] Issue #{r['issue_number']} → {r['detail']}")

    print(f"\n代码审核: {len(review)} 条")
    for r in review:
        print(f"  [{r['status']}] Issue #{r['issue_number']} ← PR #{r['pr_number']}: {r['detail']}")

    print(f"\n状态监控: {len(monitor)} 条")
    for r in monitor:
        print(f"  [{r['status']}] Issue #{r['issue_number']} ← PR #{r['pr_number']}: {r['detail']}")


def _cmd_loop() -> None:
    """discover → verify → sleep → repeat。"""
    from config import LOOP_SLEEP_SECONDS
    from utils import logger

    logger.info("loop 模式启动，间隔 %s 秒。Ctrl+C 退出。", LOOP_SLEEP_SECONDS)
    while True:
        try:
            _cmd_discover()
            _cmd_verify()
            logger.info("下一个周期: %s 秒后", LOOP_SLEEP_SECONDS)
            time.sleep(LOOP_SLEEP_SECONDS)
        except KeyboardInterrupt:
            logger.info("收到中断信号，退出 loop 模式。")
            break
        except Exception as e:
            logger.error("loop 周期异常: %s，%s 秒后重试", e, LOOP_SLEEP_SECONDS)
            time.sleep(LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    main()
