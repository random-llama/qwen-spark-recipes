# Runtime provenance

Allowlisted public-source files were collected from the reviewed frozen runtime.
The checkpoint and image are pinned in `../.env.example`; no qualification
files or model artifacts are included. The 47k vocabulary contains token IDs
only, not the corpus used to rank them.

| File | SHA-256 |
|---|---|
| `patches/build_ple_packed_table.py` | `35da4312f5c9c442eea85445d6f6712c9bb3a3b7c6caccec412da57000b02475` |
| `patches/draft_vocab_en_code_47k.txt` | `20e36b6e8eae2598019298959a578ef8adc2948bbed7189e43a8da9b9d84a0b1` |
| `patches/patch_modelopt_mxfp8.py` | `df1ea579a43b855147cd5df93998469da7c768bc9d38be28b3b77b8c30447368` |
| `patches/patch_mtp_draft_vocab.py` | `2c7d19b8021f2c439920ae7f7df6f7b008eb635256a8423ef03e168d3984911f` |
| `patches/patch_ple_layer.py` | `e3c4dbd823fb21681c74a14bacbe86d87d3c11df215f143d7556ea8533ebe7ea` |
| `patches/patch_ple_offload.py` | `0a86b26a5644736eeca7ce660a865b1187a9d99c70a1de04b7b9bdf1ee223a88` |
| `patches/patch_qsa_fp8_kv.py` | `4e64e34b2e2938be8b7def8fd09f9efa0af044afcc2f69ded9a9b7b770e416bb` |
| `patches/patch_qwen_gdn_meta_device.py` | `0b3ee831747c5c688e9669da8048c7c47fe7d0063cd7c8fb579d98b2c8b1e7e2` |

Four read-only vLLM overlays retain Apache-2.0 SPDX headers. The separate strict-defaults middleware is original AGPL-3.0-or-later code.

| Overlay | SHA-256 |
|---|---|
| `overlays/vllm/parser/abstract_parser.py` | `47351c6c0f65693ca147fd36c0fe2641bca468ffbd6b3099d16e03ada5a1cc1a` |
| `overlays/vllm/parser/parser_manager.py` | `d9f9ad43aabfca08186a3b92fd27e01c877caa72ea23db9ec22b1b9b894d328b` |
| `overlays/vllm/parser/engine/parser_engine.py` | `c23f06d6bcb67f8dc0c0ad675f8ca2ae17f095f76f34e4d85da995dc9e26b860` |
| `overlays/vllm/v1/structured_output/backend_xgrammar.py` | `e5b0c492195175ad1379b123a63fcd99c94aa1f2d9a8b4655d7e2d2e53f16de6` |
| `overlays/middleware/spark_strict_tool_defaults.py` | `8f5ee7558c1c1a52994acb5475826cdcc0e2d01419304aacce67881661494e37` |

The authoritative base pin is the immutable image digest in the recipe. Accepted
responses reported vLLM fingerprint `vllm-0.1.dev20073+g8e685d198-b796f977`.
This records the observed abbreviated version; it does not substitute an
unverified full upstream Git revision for the image digest.

Hashes refer to distributed UTF-8/LF file bytes. Copied sources had line endings normalized for Git; this can change a file hash without changing its code.
