"""Exchange a delegated refresh token without exposing it in errors or logs.

Storage is deliberately injected: the caller must persist each replacement
securely before using the access token. This module never prints credentials.
"""
import requests

TOKEN_URL = ('https://login.microsoftonline.com/'
             'dfb66dc4-3f3c-492c-991d-727dbd1c89d4/oauth2/v2.0/token')
CLIENT_ID = '44b1a606-bf62-4fc3-8546-69f99a66061a'


def exchange_refresh_token(refresh_token, persist_replacement, session=None):
    if not refresh_token or not callable(persist_replacement):
        raise ValueError('A refresh token and secure replacement storage are required')
    client = session or requests.Session()
    try:
        response = client.post(TOKEN_URL, timeout=30, data={
            'client_id': CLIENT_ID,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'scope': 'User.Read Files.ReadWrite offline_access',
        })
        if response.status_code != 200:
            raise RuntimeError(f'Microsoft token exchange failed (HTTP {response.status_code})')
        payload = response.json()
    except (requests.RequestException, ValueError):
        raise RuntimeError('Microsoft token exchange failed; details withheld') from None
    access, replacement = payload.get('access_token'), payload.get('refresh_token')
    if not isinstance(access, str) or not access or not isinstance(replacement, str) or not replacement:
        raise RuntimeError('Microsoft did not return both required tokens')
    try:
        persist_replacement(replacement)
    except Exception:
        raise RuntimeError('Replacement token could not be saved securely; no access token released') from None
    return access
