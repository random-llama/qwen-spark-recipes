#!/usr/bin/env python3
"""Validate a saved synthetic benchmark receipt; this utility never contacts an endpoint."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

EXPECTED = {"context": 28, "thinking": 2, "tool": 8, "tool_followup": 8, "vision": 1, "code": 21, "overlap": 2}


def validate(document: dict) -> dict:
    records = document.get("records") or []
    counts = Counter(record.get("scenario", {}).get("kind") for record in records)
    reasons: list[str] = []
    if document.get("state") != "complete": reasons.append("state")
    if document.get("foreign_traffic_detected") is not False: reasons.append("foreign_traffic")
    if counts != EXPECTED: reasons.append("scenario_counts")
    if len({record.get("label") for record in records}) != len(records): reasons.append("duplicate_labels")
    if not all(record.get("protocol_valid") for record in records): reasons.append("protocol")
    if document.get("accepted_http_200_requests") != 70 or document.get("completed_inferences") != 70 or document.get("grading_or_protocol_failures") != 0: reasons.append("accepted_requests")
    rows = lambda kind: [record for record in records if record.get("scenario", {}).get("kind") == kind]
    cells = [(c, size, phase) for c in (1, 2, 4) for size in ("11k", "45k") for phase in ("fresh", "repeat")]
    if not all(sum(record["scenario"].get("c") == c and record["scenario"].get("size") == size and record["scenario"].get("phase") == phase for record in rows("context")) == c for c, size, phase in cells): reasons.append("context_matrix")
    tool_cells = [(choice, thinking, stream) for choice in ("auto", "named") for thinking in (False, True) for stream in (False, True)]
    if not all(sum(record["scenario"].get("choice") == choice and record["scenario"].get("thinking") == thinking and record["scenario"].get("stream") == stream for record in rows("tool")) == 1 and sum(record["scenario"].get("choice") == choice and record["scenario"].get("thinking") == thinking and record["scenario"].get("stream") == stream for record in rows("tool_followup")) == 1 for choice, thinking, stream in tool_cells): reasons.append("tool_matrix")
    if not all(record.get("tool_valid") for record in rows("tool")): reasons.append("tool_validation")
    if not all(record.get("followup_valid") for record in rows("tool_followup")): reasons.append("tool_followup_validation")
    if not all(record.get("code_valid") for record in rows("code")): reasons.append("code_validation")
    if not all(record.get("content", "").strip() == "323" for record in rows("thinking")): reasons.append("thinking_validation")
    if not any("red,blue,green,yellow" in record.get("content", "").replace(" ", "").lower() for record in rows("vision")): reasons.append("vision_validation")
    if sum(record.get("scenario", {}).get("role") == "decode" for record in rows("overlap")) != 1 or sum(record.get("scenario", {}).get("role") == "prefill" and record.get("overlap_proven") for record in rows("overlap")) != 1: reasons.append("overlap_validation")
    return {"valid": not reasons, "records": len(records), "counts": dict(counts), "reasons": reasons}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args(argv)
    result = validate(json.loads(args.receipt.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
