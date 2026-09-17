# Third-party notices

Recipe scripts and copied patch sources are AGPL-3.0-or-later; see [LICENSE](LICENSE).
The portable subpackage also carries `recipe/LICENSE`.

The PLE, model quantization, MTP vocabulary, and QSA patch sources are derived
from [MiaAI Lab's single-Spark recipe](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark).
Their copyright and license headers are preserved. File hashes identify the
frozen versions in `recipe/runtime/PROVENANCE.md`; this is a derivative package,
not an upstream release. Our PLE-offload source includes local modifications.

Four vLLM overlays retain their `Apache-2.0` SPDX headers and vLLM project
copyright notices. The middleware overlay is original AGPL-3.0-or-later code.
Upstream: [vllm-project/vllm](https://github.com/vllm-project/vllm). A full
copy of Apache-2.0 is in `recipe/licenses/Apache-2.0.txt`.

Modification notice (2026-09-17 publication): the four files under
`recipe/runtime/overlays/vllm/` are modified vLLM sources, carrying this
deployment's strict-tool parser and XGrammar corrections. They are not
unmodified upstream files. The standalone middleware and GDN meta-device
patch are local additions covered by the repository's AGPL-3.0-or-later license.

The recipe requires but does not redistribute
[`Mia-AiLab/Qwen3.8-Flash-Next-NVFP4`](https://huggingface.co/Mia-AiLab/Qwen3.8-Flash-Next-NVFP4).
Use it under the publisher's terms. The FP8 KV approach credits
[`lancelind/qwen3.8-Flash-DGX`](https://github.com/lancelind/qwen3.8-Flash-DGX)
(Apache-2.0); the included patch is a separate reimplementation.
