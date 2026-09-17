import ast
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
import compare_receipts
import sanitize_receipts
import validate_receipts


class BenchmarkPackageTests(unittest.TestCase):
    def receipt(self, name: str) -> dict:
        return json.loads((BENCHMARKS / "data" / name).read_text(encoding="utf-8"))

    def test_accepted_receipts_validate_and_have_no_private_endpoint(self):
        for name in ("baseline-summary.json", "turbo-summary.json"):
            document = self.receipt(name)
            self.assertTrue(validate_receipts.validate(document)["valid"])
            self.assertEqual(len(document["records"]), 70)
            self.assertEqual({record["url"] for record in document["records"]}, {sanitize_receipts.PUBLIC_ENDPOINT})

    def test_comparison_is_offline_and_records_the_ttft_result(self):
        result = compare_receipts.compare(self.receipt("baseline-summary.json"), self.receipt("turbo-summary.json"))
        self.assertEqual(result["n_per_arm"], 70)
        self.assertFalse(result["all_ttft_gates_pass"])
        self.assertGreater(result["coding_elapsed_improvement"], 0.15)
        self.assertFalse(result["eligible_for_promotion"])

    def test_published_comparison_is_reproducible_and_path_free(self):
        published = json.loads((BENCHMARKS / "data" / "comparison.json").read_text(encoding="utf-8"))
        rebuilt = compare_receipts.compare(self.receipt("baseline-summary.json"), self.receipt("turbo-summary.json"))
        self.assertEqual(published, rebuilt)
        self.assertNotIn("baseline", {key for key in published if key.endswith("path")})
        self.assertNotIn(":\\", json.dumps(published))

    def test_sanitizer_replaces_only_endpoint_metadata(self):
        fixture = {"records": [{"url": "http://private.invalid:9999/v1/chat/completions", "request": {"x": 1}, "elapsed_seconds": 1.25}]}
        self.assertEqual(sanitize_receipts.sanitize(fixture)["records"][0], {"url": sanitize_receipts.PUBLIC_ENDPOINT, "request": {"x": 1}, "elapsed_seconds": 1.25})

    def test_offline_tools_do_not_import_network_clients(self):
        imports = set()
        for path in BENCHMARKS.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name for alias in node.names)
                if isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)
        for banned in ("http.client", "requests", "urllib.request", "socket", "httpx"):
            self.assertNotIn(banned, imports)


if __name__ == "__main__":
    unittest.main()
