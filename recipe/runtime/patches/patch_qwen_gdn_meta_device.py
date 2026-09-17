#!/usr/bin/env python3
"""Fail closed if the pinned Qwen GDN meta-device constructor shape changes.

The PLE CPU worker initializes metadata under ``torch.device("meta")``.  The
pinned Qwen GDN constructor overrides that context for RMSNormGated with
``current_platform.current_device()``, which forces a CUDA allocation before
the CPU PLE worker can load its offloaded weights.  Respecting the active
PyTorch device context preserves normal GPU construction while keeping the PLE
metadata model on meta tensors.
"""
import hashlib
from pathlib import Path
import sys

SOURCE_SHA256 = "81b4dcd0952492375c93bffc2cdf45f10b45ab5e117f2e1d949a147d144e64f0"

OLD = (
    "            activation=output_gate_type,\n"
    "            device=current_platform.current_device(),\n"
)
NEW = (
    "            activation=output_gate_type,\n"
    "            # Keep the loader's active device context: CUDA for the engine,\n"
    "            # meta for the PLE CPU worker's metadata-only construction.\n"
    "            device=torch.empty(0).device,\n"
)


def patch(source: str) -> str:
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA256:
        raise RuntimeError("Pinned Qwen GDN source hash mismatch")
    if source.count(OLD) != 1:
        raise RuntimeError("Qwen GDN RMSNormGated device anchor is missing or ambiguous")
    return source.replace(OLD, NEW)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: patch_qwen_gdn_meta_device.py INPUT OUTPUT")
    source, destination = (Path(value) for value in sys.argv[1:])
    destination.write_text(patch(source.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
