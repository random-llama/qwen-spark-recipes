#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bind a freshly built packed PLE cache to a local model integrity manifest."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(cache, manifest, revision):
    files = sorted(cache.glob('*.packed_u8'))
    if not files:
        raise ValueError('no packed PLE tables')
    hashes = {}
    for table in files:
        meta_path = table.with_name(table.name + '.json')
        meta = json.loads(meta_path.read_text())
        if meta.get('snapshot') != revision:
            raise ValueError('packed PLE snapshot mismatch')
        if table.stat().st_size != meta['total_rows'] * meta['row_width']:
            raise ValueError('packed PLE size mismatch')
        for path in (table, meta_path):
            hashes[path.name] = digest(path)
    return {'revision': revision, 'model_manifest_sha256': digest(manifest), 'files': hashes}


def verify(cache, manifest, revision):
    saved = json.loads((cache / 'cache-identity.json').read_text())
    if saved != identity(cache, manifest, revision):
        raise ValueError('PLE cache identity mismatch; rebuild in a new empty directory')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['record', 'verify'])
    p.add_argument('cache', type=Path)
    p.add_argument('manifest', type=Path)
    p.add_argument('revision')
    a = p.parse_args()
    if a.mode == 'record':
        value = identity(a.cache, a.manifest, a.revision)
        with (a.cache / 'cache-identity.json').open('x') as f:
            json.dump(value, f, indent=2)
    else:
        verify(a.cache, a.manifest, a.revision)


if __name__ == '__main__':
    main()
