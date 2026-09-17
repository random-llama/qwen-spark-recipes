#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Generate the frozen derived vLLM files from the exact image, or fail closed.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=.env.example
[[ -f "$ROOT/.env" ]] || { echo "Copy .env.example to .env first." >&2; exit 2; }
source "$ROOT/.env"
[[ "${IMAGE:-}" == "vllm/vllm-openai@sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8" ]] || { echo "Unexpected IMAGE." >&2; exit 2; }
[[ "$(docker image inspect --format '{{.Id}}' "$IMAGE")" == "$IMAGE_ID" ]] || { echo "Pinned image is absent or does not match IMAGE_ID." >&2; exit 2; }
OUT="$ROOT/runtime/generated"
rm -rf "$OUT"
mkdir -p "$OUT/ple_offload/orig"
tmp="$(docker create "$IMAGE" /bin/true)"
trap 'docker rm -f "$tmp" >/dev/null 2>&1 || true' EXIT
extract() { docker cp "$tmp:$1" "$2"; }
V=/usr/local/lib/python3.12/dist-packages/vllm
extract "$V/models/qwen3_8_flash_next/nvidia/ple_layer.py" "$OUT/ple_layer_patched.py.orig"
extract "$V/model_executor/layers/quantization/modelopt.py" "$OUT/modelopt_patched.py.orig"
extract "$V/models/qwen3_8_flash_next/nvidia/ops/qsa.py" "$OUT/qsa_ops_patched.py.orig"
extract "$V/models/qwen3_8_flash_next/nvidia/qsa.py" "$OUT/qsa_nvidia_patched.py.orig"
extract "$V/models/qwen3_8_flash_next/nvidia/mtp.py" "$OUT/mtp_patched.py.orig"
extract "$V/model_executor/layers/mamba/gdn/qwen_gdn_linear_attn.py" "$OUT/qwen_gdn_linear_attn_patched.py.orig"
extract "$V/model_executor/layers/ple_offload_layer.py" "$OUT/ple_offload/orig/ple_offload_layer.py"
for f in connector worker protocol; do extract "$V/v1/ple_offload/$f.py" "$OUT/ple_offload/orig/$f.py"; done
cp "$ROOT/runtime/patches/patch_"*.py "$OUT/"
cp "$ROOT/runtime/patches/build_ple_packed_table.py" "$OUT/"
( cd "$OUT" && python3 patch_ple_layer.py && python3 patch_modelopt_mxfp8.py && python3 patch_qsa_fp8_kv.py && python3 patch_mtp_draft_vocab.py && python3 patch_qwen_gdn_meta_device.py qwen_gdn_linear_attn_patched.py.orig qwen_gdn_linear_attn_patched.py && python3 patch_ple_offload.py )
for f in ple_layer_patched.py modelopt_patched.py qsa_ops_patched.py qsa_nvidia_patched.py mtp_patched.py qwen_gdn_linear_attn_patched.py ple_offload/ple_offload_layer.py ple_offload/connector.py ple_offload/worker.py ple_offload/protocol.py; do [[ -s "$OUT/$f" ]] || { echo "Patch output missing: $f" >&2; exit 1; }; done
echo "Generated runtime mounts in $OUT"
