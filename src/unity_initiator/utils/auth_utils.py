import time
from dataclasses import dataclass
from typing import Optional

import httpx

from .logger import logger

__all__ = ["fetch_cognito_token", "get_auth_headers", "TokenManager"]


@dataclass
class TokenInfo:
    """Container for token information with expiration."""

    access_token: str
    expires_at: float  # Unix timestamp when token expires
    refresh_token: Optional[str] = None


class TokenManager:
    """Manages Cognito tokens with automatic refresh capabilities."""

    def __init__(
        self, username: str, password: str, client_id: str, region: str = "us-west-2"
    ):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.region = region
        self._token_cache: Optional[TokenInfo] = None
        self._refresh_buffer = 300  # Refresh token 5 minutes before expiration

    def get_valid_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token string or None if unable to obtain
        """
        current_time = time.time()

        # Check if we have a cached token that's still valid
        if (
            self._token_cache
            and self._token_cache.expires_at > current_time + self._refresh_buffer
        ):
            logger.debug("Using cached valid token")
            return self._token_cache.access_token

        # Token is expired or will expire soon, fetch a new one
        logger.info("Token expired or expiring soon, fetching new token")
        return self._fetch_new_token()

    def _fetch_new_token(self) -> Optional[str]:
        """Fetch a new token from Cognito."""
        url = f"https://cognito-idp.{self.region}.amazonaws.com"
        payload = {
            "AuthParameters": {"USERNAME": self.username, "PASSWORD": self.password},
            "AuthFlow": "USER_PASSWORD_AUTH",
            "ClientId": self.client_id,
        }
        headers = {
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
            "Content-Type": "application/x-amz-json-1.1",
        }

        try:
            with httpx.Client(verify=False) as client:  # nosec
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

                if "AuthenticationResult" in result:
                    auth_result = result["AuthenticationResult"]
                    access_token = auth_result["AccessToken"]

                    # Calculate expiration time (default to 1 hour if not provided)
                    expires_in = auth_result.get("ExpiresIn", 3600)  # 1 hour default
                    expires_at = time.time() + expires_in

                    # Store refresh token if available
                    refresh_token = auth_result.get("RefreshToken")

                    # Cache the token info
                    self._token_cache = TokenInfo(
                        access_token=access_token,
                        expires_at=expires_at,
                        refresh_token=refresh_token,
                    )

                    logger.info("Successfully retrieved new Cognito access token")
                    return access_token
                else:
                    logger.error(
                        "Failed to retrieve access token from Cognito response"
                    )
                    return None

        except httpx.HTTPStatusError as e:
            logger.error("HTTP error while fetching Cognito token: %s", str(e))
            return None
        except httpx.RequestError as e:
            logger.error("Request error while fetching Cognito token: %s", str(e))
            return None
        except KeyError as e:
            logger.error("Unexpected response format from Cognito: %s", str(e))
            return None

    def _refresh_token(self) -> Optional[str]:
        """
        Refresh token using refresh token (if available).
        Note: This requires the refresh token flow which may need different permissions.
        """
        if not self._token_cache or not self._token_cache.refresh_token:
            logger.warning(
                "No refresh token available, fetching new token with credentials"
            )
            return self._fetch_new_token()

        url = f"https://cognito-idp.{self.region}.amazonaws.com"
        payload = {
            "AuthParameters": {"REFRESH_TOKEN": self._token_cache.refresh_token},
            "AuthFlow": "REFRESH_TOKEN_AUTH",
            "ClientId": self.client_id,
        }
        headers = {
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
            "Content-Type": "application/x-amz-json-1.1",
        }

        try:
            with httpx.Client(verify=False) as client:  # nosec
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

                if "AuthenticationResult" in result:
                    auth_result = result["AuthenticationResult"]
                    access_token = auth_result["AccessToken"]

                    # Calculate expiration time
                    expires_in = auth_result.get("ExpiresIn", 3600)
                    expires_at = time.time() + expires_in

                    # Update cached token info
                    self._token_cache = TokenInfo(
                        access_token=access_token,
                        expires_at=expires_at,
                        refresh_token=self._token_cache.refresh_token,  # Keep the same refresh token
                    )

                    logger.info("Successfully refreshed Cognito access token")
                    return access_token
                else:
                    logger.warning(
                        "Refresh token failed, fetching new token with credentials"
                    )
                    return self._fetch_new_token()

        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.warning(
                "Token refresh failed: %s, fetching new token with credentials", str(e)
            )
            return self._fetch_new_token()

    def clear_cache(self):
        """Clear the cached token."""
        self._token_cache = None
        logger.debug("Token cache cleared")


def fetch_cognito_token(
    username: str, password: str, client_id: str, region: str = "us-west-2"
) -> Optional[str]:
    """
    Fetch a Cognito access token using username/password authentication.

    Args:
        username: Unity username
        password: Unity password
        client_id: Cognito client ID
        region: AWS region (default: us-west-2)

    Returns:
        Access token string if successful, None otherwise
    """
    token_manager = TokenManager(username, password, client_id, region)
    return token_manager.get_valid_token()


def get_auth_headers(
    auth_type: str = "basic",
    username: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None,
) -> dict:
    """
    Get authentication headers for API requests.

    Args:
        auth_type: Type of authentication ("basic" or "bearer")
        username: Username for basic auth
        password: Password for basic auth
        token: Bearer token for token auth

    Returns:
        Dictionary containing authentication headers
    """
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    if auth_type.lower() == "basic" and username and password:
        import base64

        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers["Authorization"] = f"Basic {encoded_credentials}"
    elif auth_type.lower() == "bearer" and token:
        headers["Authorization"] = f"Bearer {token}"

    return headers
