import pytest
from github_refresh_secret import API, SECRET, replace_refresh_secret, seal


class Response:
    def __init__(self, status):
        self.status_code = status
    def json(self):
        return {'key': 'public-key', 'key_id': 'key-id'}


class Session:
    def __init__(self, status=204):
        self.status = status
        self.writes = []
    def get(self, url, **kwargs):
        assert url == API + '/public-key'
        return Response(200)
    def put(self, url, **kwargs):
        self.writes.append((url, kwargs['json']))
        return Response(self.status)


def test_updates_only_named_secret_with_encrypted_content():
    session = Session()
    replace_refresh_secret('sensitive-refresh', 'sensitive-github', session,
                           encrypt=lambda value, key: 'sealed')
    assert session.writes == [(API + '/' + SECRET, {'encrypted_value': 'sealed', 'key_id': 'key-id'})]


def test_failed_update_returns_no_response_details():
    session = Session(403)
    with pytest.raises(RuntimeError, match='HTTP 403') as exc:
        replace_refresh_secret('sensitive-refresh', 'sensitive-github', session,
                               encrypt=lambda value, key: 'sealed')
    assert 'sensitive' not in str(exc.value)


def test_real_sealed_box_round_trip():
    import base64
    public = pytest.importorskip('nacl.public')
    private = public.PrivateKey.generate()
    public_key = base64.b64encode(bytes(private.public_key)).decode('ascii')
    encrypted = seal('local-test-value', public_key)
    assert 'local-test-value' not in encrypted
    assert public.SealedBox(private).decrypt(base64.b64decode(encrypted)) == b'local-test-value'
