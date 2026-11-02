"""Recheck an uploaded test batch and conditionally switch its private manifest."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote, urlparse
from verify_onedrive_receipt import verify_receipt

PROJECT = 'TSE-2026-Automacao-Privado'

def save_remote_backup(graph, receipt, content):
    """Store and reread the old manifest inside a new private batch folder."""
    api = graph.API
    path = '/'.join((PROJECT, 'batches', receipt['batch_id']))
    batch = graph._request('GET', f'{api}/me/drive/root:/{quote(path, safe="/")}').json()
    if not batch.get('id') or batch['id'] != receipt.get('remote_batch_id') or 'folder' not in batch:
        raise ValueError('Remote batch folder differs from the verified receipt')
    folder = graph.create_folder(batch['id'], 'previous_manifest')
    url = f'{api}/me/drive/items/{quote(folder, safe="")}:/manifest.json:/content'
    item = graph._request('PUT', url, data=content, headers={'Content-Type': 'application/json'}).json()
    if not item.get('id') or item.get('name') != 'manifest.json' or item.get('size') != len(content):
        raise ValueError('Remote backup metadata mismatch')
    if b''.join(graph.download(item['id'])) != content:
        raise ValueError('Remote backup content mismatch')
    return item['id']


def checked_upload_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or not any(host.endswith('.' + x) for x in ('sharepoint.com', '1drv.com', 'onedrive.com')):
        raise ValueError('Unexpected upload destination')
    return url

def activate(root: Path, reference: Path, receipt_path: Path, backup: Path, graph, progress=None):
    verify_receipt(root, reference, receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    audit = json.loads((root / 'assembly-audit.json').read_text(encoding='utf-8'))
    expected_old = json.loads(reference.read_text(encoding='utf-8-sig'))
    if backup.exists():
        raise FileExistsError(backup)
    api = graph.API
    for i, entry in enumerate(receipt['verified_files'], 1):
        path = '/'.join((PROJECT, 'batches', receipt['batch_id'], entry['dataset'], entry['name']))
        item = graph._request('GET', f'{api}/me/drive/root:/{quote(path, safe="/")}').json()
        if item.get('id') != entry['remote_item_id'] or item.get('size') != entry['bytes']:
            raise ValueError('Remote item path, ID or size changed')
        digest = hashlib.sha256()
        for block in graph.download(item['id']):
            digest.update(block)
        if digest.hexdigest() != entry['sha256']:
            raise ValueError('Remote item content changed')
        if progress:
            progress(i, len(receipt['verified_files']))
    path = PROJECT + '/manifest.json'
    item = graph._request('GET', f'{api}/me/drive/root:/{quote(path, safe="/")}').json()
    item_id, etag = item.get('id'), item.get('eTag')
    if not item_id or not etag:
        raise ValueError('Manifest has no identifier or concurrency token')
    old_data = b''.join(graph.download(item_id))
    if json.loads(old_data.decode('utf-8-sig')) != expected_old:
        raise ValueError('Live manifest differs from expected baseline; no change made')
    with backup.open('xb') as f:
        f.write(old_data)
    backup_id = save_remote_backup(graph, receipt, old_data)
    candidate = dict(expected_old)
    candidate.update(batch_id=receipt['batch_id'], status='ready', migration_snapshot=False,
                     datasets=audit['datasets'])
    content = json.dumps(candidate, ensure_ascii=False, indent=2).encode('utf-8')
    session = graph._request('POST', f'{api}/me/drive/items/{quote(item_id, safe="")}/createUploadSession',
                             headers={'If-Match': etag}, json={'deferCommit': True}).json()
    upload_url = checked_upload_url(session.get('uploadUrl', ''))
    upload = graph._request('PUT', upload_url, authorized=False, data=content,
                            headers={'Content-Length': str(len(content)),
                                     'Content-Range': f'bytes 0-{len(content)-1}/{len(content)}'})
    if upload.status_code != 202:
        raise ValueError('Unexpected staged manifest response; no explicit commit sent')
    # This recheck is not an atomic compare-and-swap.
    current = graph._request('GET', f'{api}/me/drive/items/{quote(item_id, safe="")}').json()
    if current.get('eTag') != etag:
        raise ValueError('Manifest changed before commit; no explicit commit sent')
    result = graph._request('POST', upload_url, authorized=False,
                            headers={'Content-Length': '0'}, data=b'').json()
    if result.get('id') != item_id:
        raise ValueError('Commit response differs; inspect remote state before retrying')
    actual = b''.join(graph.download(item_id))
    if actual != content:
        raise ValueError('Manifest verification failed; inspect remote state before retrying')
    return {'batch_id': receipt['batch_id'], 'remote_files_verified': len(receipt['verified_files']),
            'manifest_updated': True, 'model_refresh_started': False}
