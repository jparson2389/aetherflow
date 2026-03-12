import pytest

from aetherflow.core.oauth import MockOAuthProvider, OAuthProviderDisabledError


def test_disabled_provider_raises_on_authorization() -> None:
    provider = MockOAuthProvider()

    with pytest.raises(OAuthProviderDisabledError):
        provider.authorization_url(
            state='state-1',
            redirect_uri='https://example.test/callback',
            scopes=('read',),
        )


def test_enabled_provider_returns_tokens() -> None:
    provider = MockOAuthProvider(enabled=True)

    url = provider.authorization_url(
        state='state-2',
        redirect_uri='https://example.test/callback',
        scopes=('read', 'write'),
    )
    assert url.startswith('mock://authorize?')

    token = provider.exchange_code(
        code='auth-code',
        redirect_uri='https://example.test/callback',
    )
    assert token.access_token.startswith('mock_access_')
    assert provider.access_token() == token

    refreshed = provider.refresh_token(refresh_token='refresh-1')
    assert refreshed.access_token.startswith('mock_access_refresh-1')
