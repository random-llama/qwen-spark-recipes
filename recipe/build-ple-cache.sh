#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "$ROOT/.env" ]] || { echo "Copy .env.example to .env first." >&2; exit 2; }
source "$ROOT/.env"
[[ -d "$MODEL_DIR" && "$(basename "$MODEL_DIR")" == "$MODEL_REVISION" ]] || { echo "MODEL_DIR must be the exact revision directory." >&2; exit 2; }
[[ "$(docker image inspect --format '{{.Id}}' "$IMAGE")" == "$IMAGE_ID" ]] || { echo "Pinned image identity mismatch." >&2; exit 2; }
mkdir -p "$PLE_CACHE_DIR"
[[ -z "$(find "$PLE_CACHE_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]] || { echo "Use a new empty PLE_CACHE_DIR; existing caches are never silently reused." >&2; exit 2; }
( cd "$MODEL_DIR" && sha256sum -c "$MODEL_SHA256_MANIFEST" )
docker run --rm --memory 6g --cpus 8 -v "$MODEL_DIR:/model:ro" -v "$PLE_CACHE_DIR:/out" -v "$ROOT/runtime/patches/build_ple_packed_table.py:/build.py:ro" --entrypoint python3 "$IMAGE" -u /build.py /model /out
find "$PLE_CACHE_DIR" -type f -name '*.packed_u8' -print -quit | grep -q . || { echo "Packed PLE table was not created." >&2; exit 1; }
python3 "$ROOT/cache_identity.py" record "$PLE_CACHE_DIR" "$MODEL_SHA256_MANIFEST" "$MODEL_REVISION"
