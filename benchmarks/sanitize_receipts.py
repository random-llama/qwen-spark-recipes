#!/usr/bin/env python3
"""Sanitize an offline synthetic benchmark receipt without making network calls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PUBLIC_ENDPOINT = "http://localhost/v1/chat/completions"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sanitize(document: dict) -> dict:
    """Replace connection metadata while retaining requests, responses, and timings."""
    if not isinstance(document.get("records"), list):
        raise ValueError("receipt must have a records list")
    for record in document["records"]:
        if "url" in record:
            record["url"] = PUBLIC_ENDPOINT
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise ValueError("--output must not already exist")
    source_hash = sha256(args.input)
    document = sanitize(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"input_sha256": source_hash, "output_sha256": sha256(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
