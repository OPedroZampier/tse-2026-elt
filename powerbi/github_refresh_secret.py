"""Replace only this project's GitHub Actions refresh-token secret.

Requires PyNaCl and a repository-scoped GitHub credential with Actions secrets
write access. Credentials are provided by the caller and never printed.
"""
import base64
import requests

API = 'https://api.github.com/repos/OPedroZampier/tse-2026-elt/actions/secrets'
SECRET = 'TSE_ONEDRIVE_REFRESH_TOKEN'


def seal(secret, public_key):
    from nacl import encoding, public
    key = public.PublicKey(public_key.encode('ascii'), encoding.Base64Encoder())
    ciphertext = public.SealedBox(key).encrypt(secret.encode('utf-8'))
    return base64.b64encode(ciphertext).decode('ascii')


def replace_refresh_secret(refresh_token, github_token, session=None, encrypt=seal):
    if not refresh_token or not github_token:
        raise ValueError('Missing credential')
    client = session or requests.Session()
    headers = {'Authorization': 'Bearer ' + github_token,
               'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28'}
    try:
        key_response = client.get(API + '/public-key', headers=headers, timeout=30)
        if key_response.status_code != 200:
            raise RuntimeError(f'GitHub public-key request failed (HTTP {key_response.status_code})')
        key = key_response.json()
        encrypted = encrypt(refresh_token, key['key'])
        result = client.put(API + '/' + SECRET, headers=headers, timeout=30,
                            json={'encrypted_value': encrypted, 'key_id': key['key_id']})
        if result.status_code not in (201, 204):
            raise RuntimeError(f'GitHub secret update failed (HTTP {result.status_code})')
    except requests.RequestException:
        raise RuntimeError('GitHub secret update failed; details withheld') from None
