# Synthetic receipt benchmark

This directory publishes an evidence package for one synthetic comparison. It includes two sanitized accepted receipts (70 requests per arm), their raw SSE traces, a synthetic quadrants image fixture, offline validation/comparison tools, and an optional live collector. The validation, comparison, and unit-test commands below make no API calls. The live collector does.

Run from the repository root with Python 3.10+:

```text
python benchmarks/validate_receipts.py benchmarks/data/baseline-summary.json
python benchmarks/validate_receipts.py benchmarks/data/turbo-summary.json
python benchmarks/compare_receipts.py --baseline benchmarks/data/baseline-summary.json --turbo benchmarks/data/turbo-summary.json --out comparison-rebuilt.json
python -m unittest discover -s tests -p "test_*.py"
```

To collect a new pair on Linux/POSIX, run the included harness once for each endpoint. It manages neither engines nor routing, and has no endpoint, model, token, or credential default:

```text
python benchmarks/live/turbo_trial.py --arm baseline --base-url http://localhost:PORT/v1 --model BASELINE_MODEL --trial-nonce NEW_NONCE --out baseline-out
python benchmarks/live/turbo_trial.py --arm turbo --base-url http://localhost:PORT/v1 --model TURBO_MODEL --trial-nonce NEW_NONCE --out turbo-out
```

Then compare `baseline-out/summary.json` and `turbo-out/summary.json` with the offline comparator after copying or passing those files to its inputs. Do not run the live collector on Windows: it intentionally requires Linux/POSIX because its generated-code check relies on `SIGALRM`/`setitimer` to fail closed rather than risking an unbounded execution.

The two receipts have nonce `138afdb0a61d776b499f75b3925afcae`, are complete, and each records 70 accepted HTTP-200 completed inferences with zero protocol/grading failures. The matrix is N=1 per arm: concurrency 1/2/4, actual measured context prompt-token counts 12,432 and 50,682, and fresh/repeat phases. `comparison.json` records all 12 visible-TTFT cells. The candidate does not meet the 10% TTFT gate in any cell. Its synthetic coding elapsed-time median is lower (0.7359 s vs. 1.0587 s; 30.5%), but its shorter outputs mean that result is not a throughput claim. The package never marks a receipt eligible for promotion. Invalid attempts are excluded from these accepted-trace receipts.

`sanitize_receipts.py` is an offline utility used to produce the included records. It replaces each per-record endpoint with `http://localhost/v1/chat/completions`; it retains payloads, response content, raw SSE, and measurement fields. See [PROVENANCE.md](PROVENANCE.md) for hashes and the precise redactions.

The live collector is adapted from the original; a reproduction must supply its own endpoint and isolation controls. Its generated-code checker uses a Python AST allowlist and `SIGALRM`/`setitimer` to bound execution. This is not a security sandbox. Run live checks only in a disposable, unprivileged Linux environment without secrets. The offline utilities preserve the recorded `code_valid` evidence without executing generated code.

This is synthetic qualification evidence, not a representative application workload or a deployment decision.
