import pytest

from powerbi_delegated_auth import exchange_refresh_token


class Response:
    status_code = 200
    def json(self):
        return {'access_token': 'private-access', 'refresh_token': 'private-replacement'}


class Session:
    def post(self, url, **kwargs):
        return Response()


def test_persists_replacement_before_releasing_access():
    saved = []
    access = exchange_refresh_token('private-original', saved.append, Session())
    assert saved == ['private-replacement']
    assert access == 'private-access'


def test_storage_error_cannot_leak_secret():
    def fail(token):
        raise ValueError('secret=' + token)
    with pytest.raises(RuntimeError) as exc:
        exchange_refresh_token('private-original', fail, Session())
    assert 'private' not in str(exc.value)


def test_http_error_does_not_include_response_body():
    class FailedSession:
        def post(self, url, **kwargs):
            result = Response()
            result.status_code = 401
            return result
    with pytest.raises(RuntimeError, match='HTTP 401'):
        exchange_refresh_token('private-original', lambda _: None, FailedSession())
