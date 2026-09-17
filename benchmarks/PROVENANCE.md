# Provenance and sanitization

The package was derived from two completed synthetic receipts with shared nonce `138afdb0a61d776b499f75b3925afcae`. The original files are not included.

| Receipt | Original SHA-256 | Sanitized SHA-256 |
| --- | --- | --- |
| baseline | `dc49f34eea77c4535bd48ecd096b795e095904b570ccab850c3bbd9a8f4f3bc9` | `015b63095c7ee5bbfa7297f9daeddff4670f23dd6eee1a79e7441721e04779d3` |
| turbo | `7bfb42b7808cad0292e4d3c503fbd3843c694fbeb7a2361b7d88b72b79652a3a` | `c2505961e8ada14651e6c077d90e2eef948cb165cbec04d0b4f6829c8562523d` |

Redactions are limited to per-record endpoint metadata: loopback addresses and machine-specific ports were replaced with `http://localhost/v1/chat/completions`. The original comparison artifact also contained private baseline and candidate directory paths; the included `comparison.json` is rebuilt from sanitized receipts and contains no path fields. No usernames, non-loopback IP addresses, private filesystem paths, credentials, API keys, authentication tokens, or engine/controller archives are included.

The sanitizer rewrites JSON formatting while changing endpoint metadata, so the sanitized files are not byte-for-byte copies of their sources. Request payloads, raw SSE strings, response content, labels, scenario data, and measurement values are retained. The fixture `data/quadrants.png` is synthetic; its SHA-256 is `2253ec94df3bacd71b5d932e33af727138a4c542009c299be19f4792d774d58e`.
