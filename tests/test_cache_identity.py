import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('cache_identity', Path(__file__).resolve().parents[1] / 'recipe/cache_identity.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CacheIdentityTests(unittest.TestCase):
    def test_cache_rejects_different_model_or_changed_table(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            manifest = cache / 'model-manifest'
            manifest.write_text('source weights v1')
            table = cache / 'layer.packed_u8'
            table.write_bytes(b'abcd')
            metadata = table.with_name(table.name + '.json')
            metadata.write_text(json.dumps({'snapshot': 'rev1', 'total_rows': 2, 'row_width': 2}))
            (cache / 'cache-identity.json').write_text(json.dumps(m.identity(cache, manifest, 'rev1')))
            m.verify(cache, manifest, 'rev1')
            manifest.write_text('source weights v2')
            with self.assertRaises(ValueError): m.verify(cache, manifest, 'rev1')
            manifest.write_text('source weights v1')
            table.write_bytes(b'zzzz')  # Same size must still be rejected.
            with self.assertRaises(ValueError): m.verify(cache, manifest, 'rev1')
            table.write_bytes(b'abcd')
            with self.assertRaises(ValueError): m.verify(cache, manifest, 'rev2')

    def test_cache_requires_tables_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            manifest = cache / 'model-manifest'
            manifest.write_text('weights')
            with self.assertRaises(ValueError): m.identity(cache, manifest, 'rev1')
            (cache / 'layer.packed_u8').write_bytes(b'abcd')
            with self.assertRaises(FileNotFoundError): m.identity(cache, manifest, 'rev1')
