"""Provider-agnostic OAuth interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlencode

from loguru import logger


class OAuthProviderDisabledError(RuntimeError):
    """Raised when OAuth operations are requested while disabled."""


class OAuthProvider(Protocol):
    """OAuth provider contract for standard authorization flows."""

    def is_enabled(self) -> bool:
        """Return whether the provider is enabled."""
        ...

    def authorization_url(
        self,
        *,
        state: str,
        redirect_uri: str,
        scopes: tuple[str, ...],
    ) -> str:
        """Return the authorization URL for the provider.

        Args:
            state: CSRF protection state token.
            redirect_uri: Callback URI for the authorization flow.
            scopes: Requested OAuth scopes.

        Returns:
            The authorization URL to present to the user.

        """
        ...

    def exchange_code(
        self,
        *,
        code: str,
        redirect_uri: str,
    ) -> OAuthToken:
        """Exchange an authorization code for an access token.

        Args:
            code: Authorization code returned from the provider.
            redirect_uri: Callback URI used in the authorization flow.

        Returns:
            The retrieved OAuth token.

        """
        ...

    def refresh_token(self, *, refresh_token: str) -> OAuthToken:
        """Refresh an OAuth token using a refresh token.

        Args:
            refresh_token: Refresh token value.

        Returns:
            The refreshed OAuth token.

        """
        ...

    def access_token(self) -> OAuthToken | None:
        """Return the cached access token if available."""
        ...


@dataclass(frozen=True, slots=True)
class OAuthToken:
    """OAuth token container."""

    access_token: str
    refresh_token: str | None
    token_type: str
    expires_at: datetime | None
    scopes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MockOAuthProvider:
    """Disabled OAuth provider used as a safe fallback."""

    enabled: bool = False
    _token: OAuthToken | None = None

    def is_enabled(self) -> bool:
        """Return whether the provider is enabled."""
        return self.enabled

    def authorization_url(
        self,
        *,
        state: str,
        redirect_uri: str,
        scopes: tuple[str, ...],
    ) -> str:
        """Return a mock authorization URL.

        Args:
            state: CSRF protection state token.
            redirect_uri: Callback URI for the authorization flow.
            scopes: Requested OAuth scopes.

        Returns:
            A mock authorization URL.

        Raises:
            OAuthProviderDisabledError: If the provider is disabled.

        """
        self._ensure_enabled()
        params = urlencode(
            {
                'state': state,
                'redirect_uri': redirect_uri,
                'scope': ' '.join(scopes),
            }
        )
        url = f'mock://authorize?{params}'
        logger.debug('Generated mock authorization URL.')
        return url

    def exchange_code(
        self,
        *,
        code: str,
        redirect_uri: str,
    ) -> OAuthToken:
        """Exchange an authorization code for a mock token.

        Args:
            code: Authorization code returned from the provider.
            redirect_uri: Callback URI used in the authorization flow.

        Returns:
            The retrieved OAuth token.

        Raises:
            OAuthProviderDisabledError: If the provider is disabled.

        """
        self._ensure_enabled()
        logger.debug(
            'Mock OAuth code exchange requested with redirect_uri={}.',
            redirect_uri,
        )
        token = self._build_token(access_token=f'mock_access_{code}', scopes=())
        object.__setattr__(self, '_token', token)
        logger.debug('Mock OAuth code exchanged for token.')
        return token

    def refresh_token(self, *, refresh_token: str) -> OAuthToken:
        """Refresh an OAuth token using a refresh token.

        Args:
            refresh_token: Refresh token value.

        Returns:
            The refreshed OAuth token.

        Raises:
            OAuthProviderDisabledError: If the provider is disabled.

        """
        self._ensure_enabled()
        token = self._build_token(
            access_token=f'mock_access_{refresh_token}',
            refresh_token=refresh_token,
            scopes=(),
        )
        object.__setattr__(self, '_token', token)
        logger.debug('Mock OAuth token refreshed.')
        return token

    def access_token(self) -> OAuthToken | None:
        """Return the cached access token if available."""
        return self._token

    def _ensure_enabled(self) -> None:
        """Ensure the provider is enabled.

        Raises:
            OAuthProviderDisabledError: If the provider is disabled.

        """
        if not self.enabled:
            raise OAuthProviderDisabledError('OAuth provider is disabled.')

    def _build_token(
        self,
        *,
        access_token: str,
        refresh_token: str | None = None,
        scopes: tuple[str, ...],
    ) -> OAuthToken:
        """Build a mock OAuth token.

        Args:
            access_token: Access token value.
            refresh_token: Optional refresh token value.
            scopes: Granted scopes.

        Returns:
            OAuth token container.

        """
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        return OAuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type='Bearer',
            expires_at=expires_at,
            scopes=scopes,
        )
