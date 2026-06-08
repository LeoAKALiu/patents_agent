#!/usr/bin/env python3
"""Scrape authorized CNIPA patents for golden-set construction.

Usage: python3 scripts/scrape_golden_set.py --count 17 --output golden_set/v1/

Currently implements manual entry: prompts the operator to search CNIPA
or Google Patents, paste the patent text, and the script formats it as
the standard golden-set JSON schema.
"""

import json
import sys
from pathlib import Path


def prompt_patent(index: int) -> dict:
    """Interactive prompt for one patent."""
    print(f"\n{'='*60}")
    print(f"Patent #{index}")
    print(f"{'='*60}")

    patent_id = input("Patent ID (e.g. CN202310000001B): ").strip()
    title = input("Title: ").strip()
    tech = input("Technical field [ai_software/mechanical/electronics/chemical]: ").strip()

    print("\nPaste description_full (技术领域\\n背景技术\\n发明内容\\n具体实施方式). End with '###':")
    desc_lines = []
    while True:
        line = input()
        if line.strip() == "###":
            break
        desc_lines.append(line)
    description_full = "\n".join(desc_lines)

    print("\nPaste drawings_description. End with '###':")
    drawings_lines = []
    while True:
        line = input()
        if line.strip() == "###":
            break
        drawings_lines.append(line)
    drawings_description = "\n".join(drawings_lines)

    print("\nPaste claims (one per line, format: 'N|kind|category|depends_on|preamble|feature1;feature2'). End with '###':")
    claims = []
    while True:
        line = input()
        if line.strip() == "###":
            break
        parts = line.strip().split("|")
        if len(parts) >= 6:
            claims.append({
                "number": int(parts[0]),
                "kind": parts[1],
                "category": parts[2],
                "depends_on": int(parts[3]) if parts[3] and parts[3] != "null" else None,
                "preamble": parts[4],
                "features": [f.strip() for f in parts[5].split(";") if f.strip()],
            })

    print("\nPaste description_sections as JSON {technical_field, background, summary, embodiments}:")
    desc_sections = json.loads(input())

    print("\nPaste figures as JSON [{figure_no, title}, ...]:")
    figures = json.loads(input())

    return {
        "id": patent_id,
        "title": title,
        "technical_field": tech,
        "publication_date": "",
        "claims_count": len(claims),
        "input": {
            "description_full": description_full,
            "drawings_description": drawings_description,
        },
        "ground_truth": {
            "claims": claims,
            "description_sections": desc_sections,
            "figures": figures,
        },
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scrape golden-set patents")
    parser.add_argument("--count", type=int, default=17)
    parser.add_argument("--output", type=str, default="golden_set/v1/")
    args = parser.parse_args()

    out_dir = Path(args.output)
    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"version": "v1", "entries": []}

    for i in range(1, args.count + 1):
        patent = prompt_patent(i)
        patent_file = out_dir / f"{patent['id']}.json"
        patent_file.write_text(json.dumps(patent, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["entries"].append({
            "id": patent["id"],
            "title": patent["title"],
            "technical_field": patent["technical_field"],
            "claims_count": patent["claims_count"],
        })
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  -> saved {patent_file}")

    print(f"\nDone. {len(manifest['entries'])} patents in {out_dir}")


if __name__ == "__main__":
    main()
