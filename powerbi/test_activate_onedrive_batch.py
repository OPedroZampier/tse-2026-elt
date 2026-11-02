import hashlib
import json
import pytest
import activate_onedrive_batch as module

class Response:
    def __init__(self, data=None, status=200):
        self.data, self.status_code = data or {}, status
    def json(self):
        return self.data

class FakeGraph:
    API = 'https://graph.microsoft.com/v1.0'
    def __init__(self, old, changed=False):
        self.old, self.changed, self.content, self.calls = old, changed, None, []
    def _request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if method == 'GET' and 'part-00001.csv' in url:
            return Response({'id': 'part', 'size': 4})
        if method == 'GET':
            return Response({'id': 'manifest', 'eTag': 'old-etag'})
        if method == 'POST' and kwargs.get('authorized') is not False:
            assert kwargs['headers']['If-Match'] == 'old-etag'
            return Response({'uploadUrl': 'https://test.sharepoint.com/upload?secret=x'})
        if method == 'PUT' and kwargs.get('authorized') is False:
            self.content = kwargs['data']
            return Response(status=202)
        assert method == 'POST' and kwargs.get('authorized') is False
        assert kwargs['headers']['Content-Length'] == '0'
        self.old = self.content
        return Response({'id': 'manifest'})
    def download(self, item):
        yield (b'oops' if self.changed else b'data') if item == 'part' else self.old

def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'verify_receipt', lambda *_: None)
    (tmp_path / 'assembly-audit.json').write_text(json.dumps({'datasets': {'A': {}}}))
    reference = tmp_path / 'reference.json'
    reference.write_text(json.dumps({'batch_id': 'old', 'status': 'ready', 'datasets': {}}))
    receipt = tmp_path / 'receipt.json'
    receipt.write_text(json.dumps({'batch_id': '20261031T225800Z', 'verified_files': [
        {'dataset': 'A', 'name': 'part-00001.csv', 'bytes': 4, 'remote_item_id': 'part',
         'sha256': hashlib.sha256(b'data').hexdigest()}]}))
    return reference, receipt, reference.read_bytes()

def test_switch_is_guarded_and_old_manifest_is_backed_up(tmp_path, monkeypatch):
    reference, receipt, old = setup(tmp_path, monkeypatch)
    graph = FakeGraph(old)
    result = module.activate(tmp_path, reference, receipt, tmp_path / 'backup.json', graph)
    assert result['manifest_updated'] and not result['model_refresh_started']
    assert (tmp_path / 'backup.json').read_bytes() == old
    assert json.loads(graph.old)['batch_id'] == '20261031T225800Z'
    assert graph.calls[-1][0] == 'POST' and graph.calls[-1][2]['authorized'] is False

def test_changed_remote_content_prevents_switch(tmp_path, monkeypatch):
    reference, receipt, old = setup(tmp_path, monkeypatch)
    graph = FakeGraph(old, changed=True)
    with pytest.raises(ValueError, match='content changed'):
        module.activate(tmp_path, reference, receipt, tmp_path / 'backup.json', graph)
    assert not any(method == 'PUT' for method, _, _ in graph.calls)

def test_changed_manifest_prevents_switch(tmp_path, monkeypatch):
    reference, receipt, old = setup(tmp_path, monkeypatch)
    graph = FakeGraph(b'{"batch_id":"different"}')
    with pytest.raises(ValueError, match='differs'):
        module.activate(tmp_path, reference, receipt, tmp_path / 'backup.json', graph)
    assert not any(method in ('PUT', 'POST') for method, _, _ in graph.calls)
