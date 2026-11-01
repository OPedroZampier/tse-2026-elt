import hashlib
import json
import pytest
import requests
import powerbi_onedrive_stage as uploader


class FakeGraph:
    def __init__(self, corrupt=False):
        self.items = {}
        self.corrupt = corrupt

    def project_batches_folder(self):
        return 'project/batches'

    def create_folder(self, parent, name):
        target = parent + '/' + name
        if target in self.items:
            raise FileExistsError(target)
        self.items[target] = None
        return target

    def upload_new(self, folder, name, path, chunk_size):
        assert chunk_size % (320 * 1024) == 0
        target = folder + '/' + name
        if target in self.items:
            raise FileExistsError(target)
        self.items[target] = path.read_bytes()
        return {'id': target, 'size': len(self.items[target])}

    def download(self, remote_id):
        data = self.items[remote_id]
        yield data + b'changed' if self.corrupt else data


def setup_batch(tmp_path, monkeypatch):
    path = tmp_path / 'Candidatos' / 'part-00001.csv'
    path.parent.mkdir()
    path.write_bytes(b'data')
    (tmp_path / 'assembly-audit.json').write_text(json.dumps({'datasets': {'Candidatos': {
        'files': [{'name': path.name, 'bytes': 4, 'sha256': hashlib.sha256(b'data').hexdigest()}]}}}))
    monkeypatch.setattr(uploader, 'verify', lambda *_: {'local_integrity_verified': True, 'publication_allowed': False})


def test_stages_and_verifies_without_updating_manifest(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch)
    graph = FakeGraph()
    events = []
    result = uploader.stage(tmp_path, tmp_path / 'reference', graph, '20261031T220000Z',
                            lambda *args: events.append(args))
    assert result['remote_content_verified'] and not result['manifest_updated']
    assert not result['publication_allowed']
    assert result['verified_files'] == [{'dataset': 'Candidatos', 'name': 'part-00001.csv',
                                         'bytes': 4, 'sha256': hashlib.sha256(b'data').hexdigest(),
                                         'remote_item_id': 'project/batches/20261031T220000Z/Candidatos/part-00001.csv'}]
    assert events == [(1, 1, 'Candidatos')]
    with pytest.raises(FileExistsError):
        uploader.stage(tmp_path, tmp_path / 'reference', graph, '20261031T220000Z')


def test_remote_content_mismatch_fails_closed(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='Remote content mismatch'):
        uploader.stage(tmp_path, tmp_path / 'reference', FakeGraph(corrupt=True), '20261031T220000Z')


def test_rejects_unsafe_batch_id_before_remote_access(tmp_path):
    with pytest.raises(ValueError, match='Invalid batch'):
        uploader.stage(tmp_path, tmp_path / 'ref', FakeGraph(), '../other')


class Response:
    def __init__(self, status, value):
        self.status_code, self.value = status, value

    def json(self):
        return self.value


class Session:
    def __init__(self, upload_url):
        self.upload_url = upload_url
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if method == 'POST':
            return Response(200, {'uploadUrl': self.upload_url})
        return Response(201, {'id': 'id', 'name': 'part-00001.csv', 'size': 4})


def test_upload_session_never_receives_graph_bearer_token(tmp_path):
    path = tmp_path / 'part-00001.csv'
    path.write_bytes(b'data')
    session = Session('https://site.sharepoint.com/upload?temporary=secret')
    graph = uploader.GraphTransport('test-token', session=session)
    assert graph.upload_new('folder', path.name, path, uploader.CHUNK_SIZE)['size'] == 4
    assert session.calls[0][2]['headers']['Authorization'] == 'Bearer test-token'
    assert 'Authorization' not in session.calls[1][2]['headers']


def test_rejects_untrusted_upload_url(tmp_path):
    path = tmp_path / 'part-00001.csv'
    path.write_bytes(b'data')
    session = Session('https://example.com/upload')
    with pytest.raises(ValueError, match='Unexpected Microsoft'):
        uploader.GraphTransport('test-token', session=session).upload_new('folder', path.name, path, uploader.CHUNK_SIZE)
    assert len(session.calls) == 1


def test_network_exception_is_redacted():
    class BrokenSession:
        def request(self, *args, **kwargs):
            raise requests.ConnectionError('access_token=should-not-appear')
    graph = uploader.GraphTransport('credential', session=BrokenSession())
    with pytest.raises(RuntimeError) as error:
        graph.project_batches_folder()
    assert 'credential' not in str(error.value)
    assert 'should-not-appear' not in str(error.value)


def test_authorization_is_never_sent_to_external_hosts():
    graph = uploader.GraphTransport('credential', session=Session('https://site.sharepoint.com/upload'))
    with pytest.raises(ValueError, match='outside Graph'):
        graph._request('GET', 'https://example.com/')
