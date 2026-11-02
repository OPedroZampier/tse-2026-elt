import hashlib
import json

import pytest

from fetch_powerbi_reference import fetch_reference


class Response:
    def __init__(self, value):
        self.value = value

    def json(self):
        return self.value


class FakeGraph:
    API = 'https://graph.example/v1.0'

    def __init__(self):
        self.candidate = b'DT_GERACAO\n31/10/2026\n'
        self.manifest = {'status': 'ready', 'batch_id': '20261031T225800Z', 'datasets': {'Candidatos': {'files': [{
            'name': 'part-00001.csv', 'bytes': len(self.candidate), 'sha256': hashlib.sha256(self.candidate).hexdigest()}]}}}
        self.etag = 'v1'

    def _request(self, method, url):
        if url.endswith('/manifest.json'):
            return Response({'id': 'manifest', 'eTag': 'v1'})
        if '/batches/' in url:
            return Response({'id': 'candidate', 'size': len(self.candidate)})
        return Response({'eTag': self.etag})

    def download(self, item):
        yield json.dumps(self.manifest).encode() if item == 'manifest' else self.candidate


def test_fetches_only_verified_reference(tmp_path):
    graph = FakeGraph()
    result = fetch_reference(graph, tmp_path / 'reference')
    assert result['baseline'].read_bytes() == graph.candidate
    assert json.loads(result['manifest'].read_bytes()) == graph.manifest


@pytest.mark.parametrize('failure', ['status', 'hash', 'etag'])
def test_no_output_if_reference_invalid(tmp_path, failure):
    graph = FakeGraph()
    if failure == 'status':
        graph.manifest['status'] = 'incomplete'
    elif failure == 'hash':
        graph.manifest['datasets']['Candidatos']['files'][0]['sha256'] = '0' * 64
    else:
        graph.etag = 'v2'
    output = tmp_path / 'reference'
    with pytest.raises(ValueError):
        fetch_reference(graph, output)
    assert not output.exists()


def test_rejects_stream_that_exceeds_declared_size(tmp_path):
    graph = FakeGraph()
    original_download = graph.download
    def oversized(item):
        yield from original_download(item)
        if item == 'candidate':
            yield b'extra'
    graph.download = oversized
    output = tmp_path / 'reference'
    with pytest.raises(ValueError, match='exceeds'):
        fetch_reference(graph, output)
    assert not output.exists()
