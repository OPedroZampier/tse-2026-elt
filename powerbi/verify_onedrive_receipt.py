"""Check a staging receipt against the local batch without activating it."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from verify_assembled_staging import verify

def verify_receipt(root: Path, reference: Path, receipt_path: Path):
    local = verify(root, reference)
    audit = json.loads((root / 'assembly-audit.json').read_text(encoding='utf-8'))
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if (not re.fullmatch(r'\d{8}T\d{6}Z', receipt.get('batch_id', ''))
            or not isinstance(receipt.get('remote_batch_id'), str)
            or not receipt['remote_batch_id']
            or receipt.get('remote_content_verified') is not True
            or receipt.get('manifest_updated') is not False
            or receipt.get('publication_allowed') is not False):
        raise ValueError('Unexpected receipt status')
    expected = {(name, part['name']): (part['bytes'], part['sha256'])
                for name, dataset in audit['datasets'].items() for part in dataset['files']}
    entries = receipt.get('verified_files')
    if not isinstance(entries, list) or len(entries) != local['parts'] or receipt.get('parts') != len(entries):
        raise ValueError('Missing or extra receipt entries')
    if receipt.get('datasets') != local['datasets']:
        raise ValueError('Receipt dataset count differs')
    seen, ids = set(), set()
    for entry in entries:
        key = (entry.get('dataset'), entry.get('name'))
        remote_id = entry.get('remote_item_id')
        if (key in seen or key not in expected or not isinstance(remote_id, str)
                or not remote_id or remote_id in ids
                or (entry.get('bytes'), entry.get('sha256')) != expected[key]):
            raise ValueError('Receipt file differs from verified local batch')
        seen.add(key)
        ids.add(remote_id)
    if seen != set(expected):
        raise ValueError('Receipt is incomplete')
    return {'receipt_matches_local_batch': True, 'parts': len(seen),
            'remote_currently_verified': False, 'publication_allowed': False,
            'reason': 'Remote content must be checked again before activation.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_receipt(args.root, args.reference, args.receipt), indent=2))
