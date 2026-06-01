from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.corpus.pipeline import CorpusImportService
from backend.app.rag import create_vector_index
from backend.app.settings import Settings
from backend.app.storage import SQLiteStore


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m backend.app.corpus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import an official patent export file, ZIP, or directory.")
    import_parser.add_argument("--input", required=True, type=Path)
    import_parser.add_argument("--version", default="ai-software-v1")
    import_parser.add_argument("--source", default="cnipa-export")
    import_parser.add_argument("--source-name", default="")
    import_parser.add_argument("--query", default="")
    import_parser.add_argument("--domain", default="ai_software")

    stats_parser = subparsers.add_parser("stats", help="Print corpus statistics.")
    stats_parser.add_argument("--version", default=None)

    args = parser.parse_args()
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = SQLiteStore(settings.data_dir / "patents_agent.sqlite3")
    index = create_vector_index(settings.data_dir / "chroma")
    existing_chunks = store.list_chunks()
    if existing_chunks:
        index.add(existing_chunks)
    service = CorpusImportService(store=store, index=index, data_dir=settings.data_dir)

    if args.command == "import":
        job = service.create_job(
            source_type=args.source,
            source_name=args.source_name or args.source,
            query=args.query,
            domain=args.domain,
            version_name=args.version,
        )
        service.add_input(job.id, args.input)
        completed = service.run_job(job.id)
        print(json.dumps(completed.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return

    if args.command == "stats":
        print(json.dumps(store.get_corpus_stats(version_name=args.version), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
