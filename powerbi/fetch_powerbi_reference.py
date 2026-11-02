"""Retrieve a verified private baseline using an already-authenticated Graph client.

The caller owns authentication. No tokens are persisted or printed here.
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote

PROJECT = 'TSE-2026-Automacao-Privado'


def bounded_download(graph, item_id, limit):
    content = bytearray()
    for block in graph.download(item_id):
        if len(content) + len(block) > limit:
            raise ValueError('Remote file exceeds expected size')
        content.extend(block)
    return bytes(content)


def fetch_reference(graph, output: Path):
    if output.exists():
        raise FileExistsError(output)
    root = f'{graph.API}/me/drive/root:/'
    manifest_item = graph._request('GET', root + quote(PROJECT + '/manifest.json', safe='/')).json()
    item_id, etag = manifest_item.get('id'), manifest_item.get('eTag')
    if not item_id or not etag:
        raise ValueError('Manifest metadata missing')
    data = bounded_download(graph, item_id, 4_000_000)
    manifest = json.loads(data.decode('utf-8-sig'))
    batch = manifest.get('batch_id', '')
    if manifest.get('status') != 'ready' or not re.fullmatch(r'\d{8}T\d{6}Z', batch):
        raise ValueError('Manifest is not a ready, valid batch')
    part = manifest['datasets']['Candidatos']['files'][0]
    if part.get('name') != 'part-00001.csv' or not 0 < part.get('bytes', 0) <= 40_000_000 or not re.fullmatch(r'[0-9a-f]{64}', part.get('sha256', '')):
        raise ValueError('Invalid candidate baseline metadata')
    path = f'{PROJECT}/batches/{batch}/Candidatos/{part["name"]}'
    remote = graph._request('GET', root + quote(path, safe='/')).json()
    if not remote.get('id') or remote.get('size') != part['bytes']:
        raise ValueError('Candidate baseline metadata mismatch')
    candidate = bounded_download(graph, remote['id'], part['bytes'])
    if len(candidate) != part['bytes'] or hashlib.sha256(candidate).hexdigest() != part['sha256']:
        raise ValueError('Candidate baseline integrity mismatch')
    current = graph._request('GET', f'{graph.API}/me/drive/items/{quote(item_id, safe="")}').json()
    if current.get('eTag') != etag:
        raise ValueError('Manifest changed while reading reference')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'manifest.json').write_bytes(data)
    (output / 'candidate-baseline.csv').write_bytes(candidate)
    return {'batch_id': batch, 'manifest': output / 'manifest.json', 'baseline': output / 'candidate-baseline.csv'}
