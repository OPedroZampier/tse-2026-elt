"""Bootstrap the delegated OneDrive credential without printing tokens.

The caller is responsible for securely persisting the refresh token. This
module does not activate a batch or alter a Power BI report.
"""
import time
import requests

from powerbi_delegated_auth import CLIENT_ID

BASE = 'https://login.microsoftonline.com/dfb66dc4-3f3c-492c-991d-727dbd1c89d4/oauth2/v2.0/'
SCOPE = 'User.Read Files.ReadWrite offline_access'


def bootstrap(persist, show_instructions, session=None, monotonic=time.monotonic, sleep=time.sleep):
    if not callable(persist) or not callable(show_instructions):
        raise ValueError('Secure storage and interactive instructions are required')
    client = session or requests.Session()
    try:
        response = client.post(BASE + 'devicecode', data={'client_id': CLIENT_ID, 'scope': SCOPE}, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f'Device authorization could not start (HTTP {response.status_code})')
        device = response.json()
        code, user_code = device['device_code'], device['user_code']
        uri = device['verification_uri']
        lifetime = int(device['expires_in'])
        interval = max(1, int(device.get('interval', 5)))
        if not code or not user_code or uri != 'https://microsoft.com/devicelogin' or lifetime <= 0:
            raise ValueError('Invalid device response')
        deadline = monotonic() + lifetime
        show_instructions(uri, user_code)
        while monotonic() < deadline:
            sleep(interval)
            if monotonic() >= deadline:
                break
            result = client.post(BASE + 'token', data={'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                                 'client_id': CLIENT_ID, 'device_code': code}, timeout=30)
            payload = result.json()
            if result.status_code == 200:
                refresh = payload.get('refresh_token')
                if not isinstance(refresh, str) or not refresh:
                    raise RuntimeError('Microsoft did not return a refresh token')
                try:
                    persist(refresh)
                except Exception:
                    raise RuntimeError('Credential could not be saved securely') from None
                return
            error = payload.get('error')
            if error == 'slow_down':
                interval += 5
            elif error != 'authorization_pending':
                raise RuntimeError('Microsoft device authorization failed or was declined')
        raise RuntimeError('Microsoft device authorization expired')
    except (requests.RequestException, ValueError, KeyError, TypeError):
        raise RuntimeError('Microsoft device authorization failed; details withheld') from None
