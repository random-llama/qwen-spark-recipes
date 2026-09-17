#!/usr/bin/env python3
"""Compare saved benchmark receipts offline. It contains no HTTP client code."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from validate_receipts import validate


def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def context_rows(document: dict, concurrency: int, size: str, phase: str) -> list[dict]:
    return [r for r in document["records"] if r.get("scenario", {}).get("kind") == "context" and r["scenario"].get("c") == concurrency and r["scenario"].get("size") == size and r["scenario"].get("phase") == phase]


def compare(baseline: dict, turbo: dict) -> dict:
    if baseline.get("arm") != "baseline" or turbo.get("arm") != "turbo":
        raise ValueError("receipts must be baseline and turbo")
    if baseline.get("trial_nonce") != turbo.get("trial_nonce"):
        raise ValueError("receipts must share a trial nonce")
    cells = {}
    for concurrency in (1, 2, 4):
        for size in ("11k", "45k"):
            for phase in ("fresh", "repeat"):
                key = f"c{concurrency}-{size}-{phase}"
                b = median([r["first_visible_ttft_seconds"] for r in context_rows(baseline, concurrency, size, phase) if r.get("first_visible_ttft_seconds") is not None])
                t = median([r["first_visible_ttft_seconds"] for r in context_rows(turbo, concurrency, size, phase) if r.get("first_visible_ttft_seconds") is not None])
                cells[key] = {"baseline": b, "turbo": t, "turbo_within_10_percent": b is not None and t is not None and t <= b * 1.10}
    def coding(doc: dict) -> float | None:
        return median([r["elapsed_seconds"] for r in doc["records"] if r.get("scenario", {}).get("kind") == "code"])
    b_code, t_code = coding(baseline), coding(turbo)
    improvement = (b_code - t_code) / b_code if b_code and t_code else None
    quality = {"baseline": validate(baseline), "turbo": validate(turbo)}
    return {"schema": 1, "claim": "synthetic latency evidence only; this is not a throughput claim", "trial_nonce": baseline["trial_nonce"], "n_per_arm": len(baseline["records"]), "per_class_visible_ttft_seconds": cells, "baseline_coding_elapsed_median_seconds": b_code, "turbo_coding_elapsed_median_seconds": t_code, "coding_elapsed_improvement": improvement, "quality": quality, "all_ttft_gates_pass": all(cell["turbo_within_10_percent"] for cell in cells.values()), "eligible_for_promotion": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--turbo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.out.exists(): raise ValueError("--out must not already exist")
    result = compare(json.loads(args.baseline.read_text(encoding="utf-8")), json.loads(args.turbo.read_text(encoding="utf-8")))
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
