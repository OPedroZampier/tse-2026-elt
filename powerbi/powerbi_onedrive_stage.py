"""Stage a verified batch in private OneDrive; NEVER update the live manifest.

The caller supplies a short-lived Graph access token in memory. This module
does not acquire, print, persist, or rotate credentials. Graph transport is
injected to permit testing without accessing a real OneDrive.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote, urlparse

import requests

from verify_assembled_staging import verify

CHUNK_SIZE = 10 * 1024 * 1024  # 32 * 320 KiB; Graph requires multiples of 320 KiB.


class GraphTransport:
    """Minimal delegated Graph client; errors never include token or upload URL."""
    API = 'https://graph.microsoft.com/v1.0'

    def __init__(self, access_token, session=None):
        if not access_token:
            raise ValueError('Missing Graph access token')
        self._token = access_token
        self._session = session or requests.Session()
        # Do not let netrc inject credentials into the pre-authorized upload URL.
        if session is None:
            self._session.trust_env = False

    def _request(self, method, url, *, authorized=True, **kwargs):
        headers = dict(kwargs.pop('headers', {}))
        if authorized:
            if not url.startswith(self.API + '/'):
                raise ValueError('Authorization cannot be sent outside Graph')
            headers['Authorization'] = 'Bearer ' + self._token
        try:
            response = self._session.request(method, url, headers=headers, timeout=120, **kwargs)
            if not 200 <= response.status_code < 300:
                code = ''
                try:
                    candidate = response.json().get('error', {}).get('code', '')
                    if isinstance(candidate, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', candidate):
                        code = f' ({candidate})'
                except (ValueError, AttributeError):
                    pass
                raise RuntimeError(f'Microsoft Graph returned HTTP {response.status_code}{code}')
            return response
        except requests.RequestException:
            raise RuntimeError('Microsoft Graph network request failed; details redacted') from None

    def project_batches_folder(self):
        path = quote('TSE-2026-Automacao-Privado/batches', safe='/')
        result = self._request('GET', f'{self.API}/me/drive/root:/{path}').json()
        if 'folder' not in result or not result.get('id'):
            raise ValueError('Expected private project batches folder')
        return result['id']

    def create_folder(self, parent, name):
        if not re.fullmatch(r'[A-Za-z0-9_]+', name):
            raise ValueError('Unsafe folder name')
        url = f'{self.API}/me/drive/items/{quote(parent, safe="")}/children'
        result = self._request('POST', url, json={'name': name, 'folder': {},
            '@microsoft.graph.conflictBehavior': 'fail'}).json()
        if 'folder' not in result or not result.get('id') or result.get('name') != name:
            raise ValueError('Folder creation response mismatch')
        return result['id']

    def upload_new(self, folder, name, path, chunk_size):
        if not re.fullmatch(r'part-\d{5}\.csv', name) or chunk_size % (320 * 1024):
            raise ValueError('Unsafe part name or invalid chunk size')
        url = f'{self.API}/me/drive/items/{quote(folder, safe="")}:/'+quote(name, safe='')+':/createUploadSession'
        result = self._request('POST', url, json={'item': {'@microsoft.graph.conflictBehavior': 'fail'}}).json()
        upload_url = result.get('uploadUrl', '')
        host = (urlparse(upload_url).hostname or '').lower()
        if urlparse(upload_url).scheme != 'https' or not any(host.endswith('.' + domain) for domain in ('sharepoint.com', '1drv.com', 'onedrive.com')):
            raise ValueError('Unexpected Microsoft upload destination')
        total = path.stat().st_size
        response = None
        with path.open('rb') as file:
            offset = 0
            while block := file.read(chunk_size):
                end = offset + len(block) - 1
                response = self._request('PUT', upload_url, authorized=False, data=block,
                    headers={'Content-Length': str(len(block)), 'Content-Range': f'bytes {offset}-{end}/{total}'})
                if end + 1 < total and response.status_code != 202:
                    raise ValueError('Unexpected intermediate upload response')
                offset = end + 1
        if not response or response.status_code not in (200, 201):
            raise ValueError('Upload did not complete')
        item = response.json()
        if not item.get('id') or item.get('name') != name:
            raise ValueError('Upload response mismatch')
        return item

    def download(self, remote_id):
        url = f'{self.API}/me/drive/items/{quote(remote_id, safe="")}/content'
        response = self._request('GET', url, stream=True)
        try:
            yield from response.iter_content(chunk_size=1024 * 1024)
        except requests.RequestException:
            raise RuntimeError('Remote verification failed; details redacted') from None
        finally:
            response.close()


def stage(root: Path, reference: Path, graph, batch_id: str, progress=None):
    if not re.fullmatch(r'\d{8}T\d{6}Z', batch_id):
        raise ValueError('Invalid batch identifier')
    checked = verify(root, reference)
    if not checked['local_integrity_verified'] or checked['publication_allowed']:
        raise ValueError('Input batch is not valid local staging')
    audit = json.loads((root / 'assembly-audit.json').read_text(encoding='utf-8'))
    total_parts = sum(len(dataset['files']) for dataset in audit['datasets'].values())
    # Fail on existing names, even when retrying; never overwrite a batch.
    parent = graph.project_batches_folder()
    batch_folder = graph.create_folder(parent, batch_id)
    verified_parts = 0
    verified_files = []
    for name, dataset in sorted(audit['datasets'].items()):
        folder = graph.create_folder(batch_folder, name)
        for part in dataset['files']:
            path = root / name / part['name']
            remote = graph.upload_new(folder, part['name'], path, CHUNK_SIZE)
            if remote['size'] != part['bytes']:
                raise ValueError(f'Remote size mismatch: {name}/{part["name"]}')
            remote_digest = hashlib.sha256()
            for chunk in graph.download(remote['id']):
                remote_digest.update(chunk)
            if remote_digest.hexdigest() != part['sha256']:
                raise ValueError(f'Remote content mismatch: {name}/{part["name"]}')
            verified_parts += 1
            verified_files.append({'dataset': name, 'name': part['name'], 'bytes': part['bytes'],
                                   'sha256': part['sha256'], 'remote_item_id': remote['id']})
            if progress:
                progress(verified_parts, total_parts, name)
    return {'batch_id': batch_id, 'remote_batch_id': batch_folder,
            'datasets': len(audit['datasets']), 'parts': verified_parts, 'verified_files': verified_files,
            'remote_content_verified': True, 'manifest_updated': False, 'publication_allowed': False}
