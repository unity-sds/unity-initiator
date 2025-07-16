"""
OAuth2 authentication utilities for proxy authentication.

This module handles OAuth2 authorization code flow for authenticating with proxies
that require OAuth2 authentication instead of direct Bearer tokens.
"""

import secrets
import time
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .logger import logger


class OAuth2Manager:
    """
    Manages OAuth2 authorization code flow for proxy authentication.

    This class handles the OAuth2 flow:
    1. Generate authorization URL
    2. Exchange authorization code for access token
    3. Refresh tokens when needed
    """

    def __init__(
        self,
        cognito_domain: str,
        client_id: str,
        redirect_uri: str,
        scope: str = "openid email profile",
        region: str = "us-west-2",
        verify_ssl: bool = True,
    ):
        """
        Initialize OAuth2 manager.

        Args:
            cognito_domain: Cognito domain (e.g., 'unitysds.auth.us-west-2.amazoncognito.com')
            client_id: OAuth2 client ID
            redirect_uri: Redirect URI configured in Cognito
            scope: OAuth2 scopes to request
            region: AWS region
            verify_ssl: Whether to verify SSL certificates (default: True for security)
        """
        self.cognito_domain = cognito_domain
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.region = region
        self.verify_ssl = verify_ssl

        # Token storage
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None

        # OAuth2 endpoints
        self.auth_endpoint = f"https://{cognito_domain}/oauth2/authorize"
        self.token_endpoint = f"https://{cognito_domain}/oauth2/token"

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate authorization URL for OAuth2 flow.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
            "nonce": secrets.token_urlsafe(32),
        }

        auth_url = f"{self.auth_endpoint}?{urlencode(params)}"
        logger.info("Generated authorization URL: %s", auth_url)
        return auth_url

    def exchange_code_for_token(self, authorization_code: str) -> dict:
        """
        Exchange authorization code for access token.

        Args:
            authorization_code: Authorization code from OAuth2 callback

        Returns:
            Token response containing access_token, refresh_token, etc.
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            with httpx.Client(verify=self.verify_ssl) as client:  # nosec B501
                response = client.post(self.token_endpoint, data=data, headers=headers)
                response.raise_for_status()
                token_data = response.json()

                # Store tokens
                self._access_token = token_data.get("access_token")
                self._refresh_token = token_data.get("refresh_token")

                # Calculate expiration
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = time.time() + expires_in

                logger.info("Successfully exchanged code for token")
                return token_data

        except httpx.HTTPStatusError as e:
            logger.error("Failed to exchange code for token: %s", str(e))
            logger.error("Response: %s", e.response.text)
            raise
        except Exception as e:
            logger.error("Error exchanging code for token: %s", str(e))
            raise

    def refresh_access_token(self) -> Optional[str]:
        """
        Refresh access token using refresh token.

        Returns:
            New access token or None if refresh failed
        """
        if not self._refresh_token:
            logger.warning("No refresh token available")
            return None

        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": self._refresh_token,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            with httpx.Client(verify=self.verify_ssl) as client:  # nosec B501
                response = client.post(self.token_endpoint, data=data, headers=headers)
                response.raise_for_status()
                token_data = response.json()

                # Update tokens
                self._access_token = token_data.get("access_token")
                if "refresh_token" in token_data:
                    self._refresh_token = token_data.get("refresh_token")

                # Update expiration
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = time.time() + expires_in

                logger.info("Successfully refreshed access token")
                return self._access_token

        except httpx.HTTPStatusError as e:
            logger.error("Failed to refresh token: %s", str(e))
            logger.error("Response: %s", e.response.text)
            return None
        except Exception as e:
            logger.error("Error refreshing token: %s", str(e))
            return None

    def get_valid_token(self, refresh_buffer: int = 300) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.

        Args:
            refresh_buffer: Seconds before expiration to refresh token

        Returns:
            Valid access token or None if unable to obtain
        """
        current_time = time.time()

        # Check if we have a valid token
        if (
            self._access_token
            and self._token_expires_at
            and self._token_expires_at > current_time + refresh_buffer
        ):
            logger.debug("Using cached valid token")
            return self._access_token

        # Token is expired or will expire soon, try to refresh
        if self._refresh_token:
            logger.info("Token expired or expiring soon, refreshing")
            return self.refresh_access_token()

        logger.warning("No valid token and no refresh token available")
        return None

    def clear_tokens(self):
        """Clear stored tokens."""
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        logger.debug("Cleared stored tokens")


def extract_authorization_code_from_url(url: str) -> Optional[str]:
    """
    Extract authorization code from OAuth2 callback URL.

    Args:
        url: OAuth2 callback URL containing authorization code

    Returns:
        Authorization code or None if not found
    """
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        # Check for authorization code
        if "code" in query_params:
            return query_params["code"][0]

        # Check for error
        if "error" in query_params:
            error = query_params["error"][0]
            error_description = query_params.get("error_description", [""])[0]
            logger.error("OAuth2 error: %s - %s", error, error_description)
            return None

        logger.warning("No authorization code found in URL")
        return None

    except Exception as e:
        logger.error("Error extracting authorization code: %s", str(e))
        return None


def get_oauth2_headers(token: str) -> dict:
    """
    Get headers for OAuth2 authenticated requests.

    Args:
        token: OAuth2 access token

    Returns:
        Headers dictionary with OAuth2 authentication
    """
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
