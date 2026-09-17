# Qwen3.8-Flash-Next on one DGX Spark

A single-Spark serving recipe derived from **[MiaAI Lab's original recipe](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark)**. Our deployment runs two independent copies: one Qwen3.8-Flash-Next TP=1 engine per NVIDIA DGX Spark. You only need one Spark to use the recipe; a second lets your agent software route separate tasks to separate engines.

This repository shares the serving recipe and a preliminary, reproducible comparison with Code Turbo. It is integration and validation work built on upstream projects—not a new model or a claim to the fastest Spark deployment.

## Credits and our contribution

- **[MiaAI Lab / @MiaAI_lab](https://x.com/MiaAI_lab)** — the foundational single-Spark recipe, the [NVFP4 checkpoint](https://huggingface.co/Mia-AiLab/Qwen3.8-Flash-Next-NVFP4), and the upstream PLE, quantization, and MTP/draft-vocabulary work used here. Primary recipe credit belongs to MiaAI Lab.
- **[Qwen / Alibaba](https://huggingface.co/Qwen)** — the underlying Qwen3.8-Flash-Next model, including its multimodal capabilities.
- **[vLLM contributors](https://github.com/vllm-project/vllm)** — the inference engine and parser/structured-output code on which our overlays are based.
- **[lancelind](https://github.com/lancelind/qwen3.8-Flash-DGX)** — the FP8 KV-cache approach, reimplemented in MiaAI Lab's QSA patch. This credit applies specifically to that approach.
- **NVIDIA** — the DGX Spark hardware platform.

**Our additions:** deployment integration and packaging, local tool-call/parser corrections, configuration qualification, and the published synthetic benchmark harness and evidence. Our two-Spark workflow is an optional deployment of two copies of the single-Spark recipe. We did not originate the model, single-Spark fit, NVFP4 quantization, or upstream MTP optimization.

The comparison candidate is credited separately to [sayyidfareed](https://huggingface.co/sayyidfareed/Qwen3.8-Flash-Next-Code-Turbo-Spark) and [Saren-Arterius](https://github.com/Saren-Arterius/qwen3.8-Flash-DGX-AutoRound). It was tested, not adopted as our retained serving profile. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for component licenses and modification notices.

## The setup

```text
Your client / agent orchestrator
    ├── Spark A: Qwen3.8 NVFP4 · TP=1 · max-num-seqs=4
    └── Spark B: Qwen3.8 NVFP4 · TP=1 · max-num-seqs=4
```

The engines are independent. The client must explicitly route work between them; running two servers does not automatically create collaboration, load balancing, or failover. Four admitted sequences is a scheduler limit, not a promise of four times the speed. Concurrent requests share memory and compute.

| Setting | Retained profile, per Spark |
|---|---|
| Model | Qwen3.8-Flash-Next, NVFP4 |
| Tensor parallelism | 1 |
| Maximum sequences | 4 |
| Maximum model length | 262,144 tokens; actual concurrent capacity depends on KV availability |
| Batched-token budget | 2,048 |
| Speculative decoding | MTP3 with a trimmed English/code draft vocabulary |
| Prefix caching | Enabled |
| Tool parser | `qwen3_xml`, with the pinned corrections in the recipe |
| Validation | Tool calls, post-tool answers, synthetic code checks, image input |

See [the recipe](recipe/README.md) for exact pins, patches, prerequisites, and packaging limits. No model weights, credentials, remote-management configuration, or private infrastructure are distributed here.

## What we actually measured

**2026-09-17: one synthetic matrix per arm, both run sequentially on the same Spark.** Each arm completed 70 valid requests, spanning C1/C2/C4, context reuse, tool calls, thinking modes, image input, and small coding checks. These are preliminary observations, not confidence intervals or broad coding-quality equivalence.

| Measurement | Retained NVFP4 | Tested Code Turbo |
|---|---:|---:|
| Functional/protocol requests passing | 70/70 | 70/70 |
| C1 fresh 12,432-token prompt: first token | 5.56 s | 9.37 s |
| C1 fresh 50,682-token prompt: first token | 22.13 s | 28.45 s |
| C1 repeated 50,682-token prompt: first token | 1.42 s | 3.44 s |
| C4 fresh 50,682-token prompts: median first token | 56.70 s | 92.97 s |
| C4 repeated 50,682-token prompts: median first token | 4.28 s | 11.64 s |
| Fixed 512-token coding generation overlapping a long prefill: elapsed | 31.12 s | 39.48 s |

The NVFP4 profile had lower first-token latency in all 12 tested context/concurrency/cache cells. We retained it. Code Turbo passed the functional checks and finished the tiny coding tasks sooner, but generated shorter answers; that does not establish higher token throughput.

The configurations differ in quantization, kernels, draft vocabulary, batch budget, and memory layout. This compares two integrated serving profiles; it does not isolate the effect of quantization. Both used the same strict-tool corrections. It does not reproduce or disprove the Turbo author's benchmarks. Two earlier invalid attempts were excluded; the evidence notes explain why.

**Read the [benchmark package](benchmarks/README.md)** for the accepted traces, exact configuration details, sanitization provenance, comparison code, and rerun instructions. Short-output token-rate estimates are deliberately not a headline result. A synthetic image check establishes API image support, not image support in every client.

## Reuse and contribute

Start with the pinned recipe, then validate on your own workload. Keep a recoverable baseline. Repeated runs, long coding generations, repository-level coding tasks, and different prompt distributions are valuable next checks.

Please include exact model/runtime revisions, input and output lengths, concurrency, cache state, raw measurements, and correctness checks when sharing results. Distinguish first-token latency, decode rate, and aggregate throughput.

Credits and component licenses are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The Turbo comparison uses [sayyidfareed's checkpoint](https://huggingface.co/sayyidfareed/Qwen3.8-Flash-Next-Code-Turbo-Spark) and [Saren-Arterius's runtime](https://github.com/Saren-Arterius/qwen3.8-Flash-DGX-AutoRound). Thanks to the model, quantization, runtime, and Spark recipe maintainers whose work makes this possible.
