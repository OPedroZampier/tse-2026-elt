"""One-time delegated authentication; print only an encrypted device code."""
import base64
import os
from pathlib import Path
import time

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from github_refresh_secret import replace_refresh_secret
from powerbi_delegated_auth import CLIENT_ID

BASE = 'https://login.microsoftonline.com/dfb66dc4-3f3c-492c-991d-727dbd1c89d4/oauth2/v2.0/'
EXPECTED_ACCOUNT = 'pedro.zandrade@sempreceub.com'


def run(session=None, clock=time.monotonic, sleep=time.sleep):
    github = os.environ.get('TSE_GITHUB_SECRETS_TOKEN', '')
    if not github:
        raise RuntimeError('Repository credential unavailable')
    client = session or requests.Session()
    response = client.post(BASE + 'devicecode', data={'client_id': CLIENT_ID,
                           'scope': 'User.Read Files.ReadWrite offline_access'}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError('Device authorization could not be started')
    data = response.json()
    public = serialization.load_pem_public_key(Path(__file__).with_name('bootstrap-public.pem').read_bytes())
    encrypted = public.encrypt(data['user_code'].encode('ascii'), padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    print('ENCRYPTED_DEVICE_CODE=' + base64.b64encode(encrypted).decode('ascii'), flush=True)
    deadline = clock() + int(data['expires_in'])
    interval = max(5, int(data.get('interval', 5)))
    while clock() < deadline:
        sleep(interval)
        token = client.post(BASE + 'token', data={'client_id': CLIENT_ID,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            'device_code': data['device_code']}, timeout=30)
        payload = token.json()
        if token.status_code == 200:
            access, refresh = payload.get('access_token'), payload.get('refresh_token')
            if not access or not refresh:
                raise RuntimeError('Required tokens were not returned')
            profile = client.get('https://graph.microsoft.com/v1.0/me',
                                 headers={'Authorization': 'Bearer ' + access}, timeout=30)
            if profile.status_code != 200 or profile.json().get('userPrincipalName', '').lower() != EXPECTED_ACCOUNT:
                raise RuntimeError('The authenticated account is not the expected university account')
            replace_refresh_secret(refresh, github)
            print('University credential saved as a GitHub Actions secret.', flush=True)
            return
        error = payload.get('error')
        if error == 'slow_down':
            interval += 5
        elif error != 'authorization_pending':
            raise RuntimeError('Microsoft authorization failed or was declined')
    raise RuntimeError('Microsoft authorization expired')


if __name__ == '__main__':
    try:
        run()
    except Exception:
        raise SystemExit('Authentication setup failed; sensitive details withheld.') from None
