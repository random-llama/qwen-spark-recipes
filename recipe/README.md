# Portable seq4 recipe

This is a frozen production-profile source package for a single isolated DGX
Spark development machine. It contains no weights, credentials, control-plane
code, host configuration, logs, SSH material, or production paths. It is an
experimental portable launcher and has not been freshly installed or GPU-tested.
The existing production deployment remained running during packaging; its
benchmark history does not validate a fresh installation of these new scripts.

Prerequisites: an idle Linux ARM64 DGX Spark, Docker with NVIDIA GPU support,
working `nvidia-smi`, Bash, Python 3.10+, and enough NVMe space for the checkpoint,
image, and approximately 27 GiB packed PLE cache. Do not run these scripts
beside an existing model server. The launcher adds `SYS_NICE`/`SYS_PTRACE` and
uses host IPC/network, matching the original container profile; use a dedicated
development machine.

| Component | Pin |
|---|---|
| Checkpoint | `Mia-AiLab/Qwen3.8-Flash-Next-NVFP4` revision `925d7be6c14c6c9442ef83e8f05b5a3c39304f69` |
| vLLM image | `vllm/vllm-openai@sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8` |
| Image identity | `sha256:d464f3b466fa9c45ddbff8a812e80564503b6879a9fd95c1a47514f3f0df5a4a` (arm64/linux) |
| Runtime source | [vllm-project/vllm](https://github.com/vllm-project/vllm), packaged by the pinned image |
| Recipe source | [MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark) |

Copy `.env.example` to `.env`, obtain the model at the exact revision under its
publisher terms, create a SHA-256 manifest for its artifact set, set absolute
local paths, then run `./prepare-runtime.sh`, `./build-ple-cache.sh`, and
`./launch.sh`. The path and manifest prevent accidental substitution; they do
not independently prove the model's publication origin. Preparation
extracts image sources and applies the frozen patches; it fails on changed
source anchors. Launch verifies the image identity and model hashes, requires
an idle GPU, rejects a colliding container name, and binds only to localhost.

From this directory, after obtaining the checkpoint and editing `.env`:

```bash
source .env
docker pull "$IMAGE"
# Save a local integrity receipt OUTSIDE the model directory. This proves
# later files match this local copy, not that they came from the publisher.
(cd "$MODEL_DIR" && find -L . -type f -print0 | sort -z | xargs -0 sha256sum) > "$MODEL_SHA256_MANIFEST"
bash prepare-runtime.sh
bash build-ple-cache.sh
bash launch.sh
docker logs -f "$CONTAINER_NAME"
```

Use the publisher's download mechanism with the exact revision above. Set
`MODEL_DIR` to that revision's snapshot directory (its final path component must
be the revision hash), `MODEL_SHA256_MANIFEST` to an absolute external filename,
and `PLE_CACHE_DIR` to a new dedicated directory for this checkpoint. Do not
reuse a packed table from another model. A cache identity receipt ties table content and metadata to the
model manifest and revision. Building requires an empty cache directory; a
partial build must be retried in a new directory. Verification reads the packed
table (about 27 GiB), so allow time for this integrity check. The draft and graph settings
are intentionally fixed in `launch.sh`; environment values do not override them.

After the server is ready, the model alias is `qwen38-flash-next` at
`http://127.0.0.1:8899/v1`. Repeat independently on the other Spark. Remote
routing and service supervision remain your responsibility; this package does
not install a background service, watchdog, or automatic restart policy.

The frozen profile is TP=1, 262,144 context, GMU 0.749, FP8 KV, BF16 SSM,
MTP3, 47,149-token local argmax, prefix caching, `qwen3_xml`, batch 2,048,
four sequences, and full-decode captures `4,8,12,16`. It includes all required
NVFP4 PLE, FP8 QSA, MTP, and GDN patches plus five read-only parser/middleware
overlays. PLE construction is mandatory and launch refuses a raw-table fallback.
Do not treat its past measurements as portable performance results.

The original production supervisor, cgroup budget derivation, health policy,
and host privileges are deliberately absent. This standalone launcher is not a
replacement for those production safeguards.

Remote access is deliberately out of scope. If required, choose an authenticated
reverse proxy, private network boundary, and firewall policy separately.

`runtime/generated/` is generated from the image and should not be committed.
Copied-source hashes are in [runtime/PROVENANCE.md](runtime/PROVENANCE.md).
