import unittest
from unittest.mock import Mock

from powerbi_device_bootstrap import bootstrap


class DeviceBootstrapTests(unittest.TestCase):
    def response(self, status, payload):
        return Mock(status_code=status, json=Mock(return_value=payload))

    def test_persists_token_without_returning_or_displaying_it(self):
        device = {'device_code': 'device-secret', 'user_code': 'ABCD',
                  'verification_uri': 'https://microsoft.com/devicelogin', 'expires_in': 600}
        session = Mock()
        session.post.side_effect = [self.response(200, device),
                                    self.response(400, {'error': 'authorization_pending'}),
                                    self.response(200, {'refresh_token': 'private-refresh'})]
        persist, show = Mock(), Mock()
        result = bootstrap(persist, show, session, monotonic=lambda: 0, sleep=lambda _: None)
        self.assertIsNone(result)
        persist.assert_called_once_with('private-refresh')
        show.assert_called_once_with('https://microsoft.com/devicelogin', 'ABCD')

    def test_storage_failure_hides_details(self):
        device = {'device_code': 'device-secret', 'user_code': 'ABCD',
                  'verification_uri': 'https://microsoft.com/devicelogin', 'expires_in': 600}
        session = Mock()
        session.post.side_effect = [self.response(200, device),
                                    self.response(200, {'refresh_token': 'private-refresh'})]
        with self.assertRaisesRegex(RuntimeError, 'saved securely') as error:
            bootstrap(Mock(side_effect=ValueError('private-refresh')), Mock(), session,
                      monotonic=lambda: 0, sleep=lambda _: None)
        self.assertNotIn('private-refresh', str(error.exception))


if __name__ == '__main__':
    unittest.main()
