#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Start a standalone development-machine instance after prepare-runtime.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "$ROOT/.env" ]] || { echo "Copy .env.example to .env first." >&2; exit 2; }
source "$ROOT/.env"
[[ -d "$MODEL_DIR" && -d "$PLE_CACHE_DIR" ]] || { echo "MODEL_DIR and PLE_CACHE_DIR must be existing absolute directories." >&2; exit 2; }
[[ "$(basename "$MODEL_DIR")" == "$MODEL_REVISION" ]] || { echo "MODEL_DIR must be the exact revision directory: $MODEL_REVISION" >&2; exit 2; }
[[ -f "$MODEL_SHA256_MANIFEST" ]] || { echo "MODEL_SHA256_MANIFEST is required to guard model artifacts." >&2; exit 2; }
if ! GPU_PROCESSES="$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)"; then
  echo "Cannot establish GPU idleness; refusing launch." >&2; exit 2
fi
[[ -z "$(printf '%s' "$GPU_PROCESSES" | tr -d '[:space:]')" ]] || { echo "GPU is not idle; refusing launch." >&2; exit 2; }
[[ "$(docker image inspect --format '{{.Id}}' "$IMAGE")" == "$IMAGE_ID" ]] || { echo "Pinned image identity mismatch." >&2; exit 2; }
OUT="$ROOT/runtime/generated"; [[ -s "$OUT/mtp_patched.py" ]] || { echo "Run ./prepare-runtime.sh first." >&2; exit 2; }
[[ -z "$(docker ps -aq --filter "name=^/${CONTAINER_NAME}$")" ]] || { echo "Container name already exists: $CONTAINER_NAME" >&2; exit 2; }
V=/usr/local/lib/python3.12/dist-packages/vllm
( cd "$MODEL_DIR" && sha256sum -c "$MODEL_SHA256_MANIFEST" )
find "$PLE_CACHE_DIR" -type f -name '*.packed_u8' -print -quit | grep -q . || { echo "Run ./build-ple-cache.sh before launch; raw PLE fallback is forbidden." >&2; exit 2; }
python3 "$ROOT/cache_identity.py" verify "$PLE_CACHE_DIR" "$MODEL_SHA256_MANIFEST" "$MODEL_REVISION"
docker run -d --name "$CONTAINER_NAME" --gpus all --network host --ipc host --memory "${CONTAINER_MEM_GIB}g" --memory-swap "${CONTAINER_MEM_GIB}g" --ulimit memlock=-1 --ulimit stack=67108864 \
  --cap-add SYS_NICE --cap-add SYS_PTRACE \
  -v "$MODEL_DIR:/model:ro" -v "$PLE_CACHE_DIR:/root/.cache/vllm/ple_cache" \
  -v "$ROOT/runtime/patches/draft_vocab_en_code_47k.txt:/root/draft_vocab.txt:ro" \
  -v "$OUT/ple_layer_patched.py:$V/models/qwen3_8_flash_next/nvidia/ple_layer.py:ro" \
  -v "$OUT/modelopt_patched.py:$V/model_executor/layers/quantization/modelopt.py:ro" \
  -v "$OUT/qsa_ops_patched.py:$V/models/qwen3_8_flash_next/nvidia/ops/qsa.py:ro" \
  -v "$OUT/qsa_nvidia_patched.py:$V/models/qwen3_8_flash_next/nvidia/qsa.py:ro" \
  -v "$OUT/mtp_patched.py:$V/models/qwen3_8_flash_next/nvidia/mtp.py:ro" \
  -v "$OUT/qwen_gdn_linear_attn_patched.py:$V/model_executor/layers/mamba/gdn/qwen_gdn_linear_attn.py:ro" \
  -v "$OUT/ple_offload/ple_offload_layer.py:$V/model_executor/layers/ple_offload_layer.py:ro" \
  -v "$OUT/ple_offload/connector.py:$V/v1/ple_offload/connector.py:ro" \
  -v "$OUT/ple_offload/worker.py:$V/v1/ple_offload/worker.py:ro" \
  -v "$OUT/ple_offload/protocol.py:$V/v1/ple_offload/protocol.py:ro" \
  -v "$ROOT/runtime/overlays/vllm/parser/abstract_parser.py:$V/parser/abstract_parser.py:ro" \
  -v "$ROOT/runtime/overlays/vllm/parser/parser_manager.py:$V/parser/parser_manager.py:ro" \
  -v "$ROOT/runtime/overlays/vllm/parser/engine/parser_engine.py:$V/parser/engine/parser_engine.py:ro" \
  -v "$ROOT/runtime/overlays/vllm/v1/structured_output/backend_xgrammar.py:$V/v1/structured_output/backend_xgrammar.py:ro" \
  -v "$ROOT/runtime/overlays/middleware/spark_strict_tool_defaults.py:/usr/local/lib/python3.12/dist-packages/spark_strict_tool_defaults.py:ro" \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e VLLM_PLE_CPU_OFFLOAD=1 -e VLLM_PLE_OFFLOAD_STEP_TIMEOUT=300 \
  -e VLLM_PLE_PACKED_TABLE_DIR=/root/.cache/vllm/ple_cache -e VLLM_MTP_DRAFT_VOCAB=/root/draft_vocab.txt \
  "$IMAGE" /model --served-model-name qwen38-flash-next --tokenizer /model --tensor-parallel-size 1 \
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" --max-num-seqs "$MAX_NUM_SEQS" --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS" --max-model-len "$MAX_MODEL_LEN" --kv-cache-dtype "$KV_CACHE_DTYPE" --mamba-ssm-cache-dtype "$MAMBA_SSM_CACHE_DTYPE" --load-format safetensors --safetensors-load-strategy lazy --enable-chunked-prefill --default-chat-template-kwargs '{"enable_thinking":false}' --reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_xml --middleware spark_strict_tool_defaults.StrictToolDefaults --enable-prefix-caching --distributed-executor-backend mp --speculative-config '{"method":"mtp","num_speculative_tokens":3,"use_local_argmax_reduction":true}' --compilation-config '{"mode":0,"cudagraph_mode":"FULL_DECODE_ONLY","cudagraph_capture_sizes":[4,8,12,16]}' --host 127.0.0.1 --port "$PORT"
