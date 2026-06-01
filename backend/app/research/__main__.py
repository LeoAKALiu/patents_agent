from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.research.public_search import (
    AnySearchClient,
    PublicSearchHit,
    build_reverse_modeling_search_plan,
    export_research_package,
    run_anysearch_plan,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m backend.app.research")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Create a public prior-art search package.")
    plan_parser.add_argument("--output", type=Path, required=True)

    anysearch_parser = subparsers.add_parser("anysearch", help="Run AnySearch for the reverse-modeling search plan.")
    anysearch_parser.add_argument("--output", type=Path, required=True)
    anysearch_parser.add_argument("--limit-per-query", type=int, default=10)
    anysearch_parser.add_argument("--max-queries", type=int, default=None)
    anysearch_parser.add_argument("--timeout-seconds", type=int, default=12)

    import_hits_parser = subparsers.add_parser("export-hits", help="Export a research package from existing hit JSON.")
    import_hits_parser.add_argument("--hits-json", type=Path, required=True)
    import_hits_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    plan = build_reverse_modeling_search_plan()

    if args.command == "plan":
        export_research_package(plan, [], args.output)
        print(json.dumps({"output": str(args.output)}, ensure_ascii=False))
        return

    if args.command == "anysearch":
        hits, errors = run_anysearch_plan(
            plan,
            client=AnySearchClient(timeout_seconds=args.timeout_seconds),
            limit_per_query=args.limit_per_query,
            max_queries=args.max_queries,
            continue_on_error=True,
        )
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "anysearch_hits.json").write_text(
            json.dumps([hit.__dict__ for hit in hits], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (args.output / "anysearch_errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs = export_research_package(plan, hits, args.output)
        print(
            json.dumps(
                {**{key: str(value) for key, value in outputs.items()}, "hits": len(hits), "errors": len(errors)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "export-hits":
        payload = json.loads(args.hits_json.read_text(encoding="utf-8"))
        hits = [
            PublicSearchHit(
                theme_id=str(item.get("theme_id", "")),
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                description=str(item.get("description", "")),
                provider=str(item.get("provider", "")),
                score=float(item.get("score", 0.0)),
                quality_score=float(item.get("quality_score", 0.0)),
                source=str(item.get("source", "")),
                content=str(item.get("content", "")),
            )
            for item in payload
        ]
        outputs = export_research_package(plan, hits, args.output)
        print(json.dumps({key: str(value) for key, value in outputs.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
