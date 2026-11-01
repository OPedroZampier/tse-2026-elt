from unittest.mock import Mock, patch
import os
import bootstrap_ci


def response(status, payload):
    return Mock(status_code=status, json=Mock(return_value=payload))


def test_only_expected_account_can_save_refresh_token(capsys):
    session = Mock()
    session.post.side_effect = [response(200, {'user_code': 'ABCD1234', 'device_code': 'hidden-device', 'expires_in': 60}),
                                response(200, {'access_token': 'hidden-access', 'refresh_token': 'hidden-refresh'})]
    session.get.return_value = response(200, {'userPrincipalName': bootstrap_ci.EXPECTED_ACCOUNT})
    with patch.dict(os.environ, {'TSE_GITHUB_SECRETS_TOKEN': 'hidden-github'}), \
         patch.object(bootstrap_ci, 'replace_refresh_secret') as save:
        bootstrap_ci.run(session, clock=lambda: 0, sleep=lambda _: None)
    save.assert_called_once_with('hidden-refresh', 'hidden-github')
    out = capsys.readouterr().out
    assert 'ENCRYPTED_DEVICE_CODE=' in out
    assert 'ABCD1234' not in out and 'hidden-' not in out


def test_unexpected_account_never_saves_token():
    session = Mock()
    session.post.side_effect = [response(200, {'user_code': 'ABCD1234', 'device_code': 'hidden-device', 'expires_in': 60}),
                                response(200, {'access_token': 'hidden-access', 'refresh_token': 'hidden-refresh'})]
    session.get.return_value = response(200, {'userPrincipalName': 'other@example.org'})
    with patch.dict(os.environ, {'TSE_GITHUB_SECRETS_TOKEN': 'hidden-github'}), \
         patch.object(bootstrap_ci, 'replace_refresh_secret') as save:
        try:
            bootstrap_ci.run(session, clock=lambda: 0, sleep=lambda _: None)
            assert False, 'Unexpected account should fail'
        except RuntimeError:
            pass
    save.assert_not_called()
