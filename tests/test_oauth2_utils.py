"""
Tests for OAuth2 authentication utilities.
"""

import time
from unittest.mock import Mock, patch
from urllib.parse import parse_qs

import httpx
import pytest

from unity_initiator.utils.oauth2_utils import (
    OAuth2Manager,
    extract_authorization_code_from_url,
    get_oauth2_headers,
)


class TestOAuth2Manager:
    """Test OAuth2Manager class."""

    def test_init(self):
        """Test OAuth2Manager initialization."""
        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
        )

        assert manager.cognito_domain == "test.auth.us-west-2.amazoncognito.com"
        assert manager.client_id == "test-client-id"
        assert manager.redirect_uri == "https://example.com/callback"
        assert manager.scope == "openid email profile"
        assert manager.region == "us-west-2"
        assert manager.verify_ssl is True
        assert (
            manager.auth_endpoint
            == "https://test.auth.us-west-2.amazoncognito.com/oauth2/authorize"
        )
        assert (
            manager.token_endpoint
            == "https://test.auth.us-west-2.amazoncognito.com/oauth2/token"
        )

    def test_init_with_verify_ssl_false(self):
        """Test initialization with verify_ssl=False."""
        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
            verify_ssl=False,
        )

        assert manager.verify_ssl is False

    def test_get_authorization_url(self):
        """Test authorization URL generation."""
        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
        )

        auth_url = manager.get_authorization_url()

        # Parse URL and check parameters
        parsed = httpx.URL(auth_url)
        params = parse_qs(
            parsed.query.decode()
            if hasattr(parsed.query, "decode")
            else str(parsed.query)
        )

        assert parsed.scheme == "https"
        assert parsed.host == "test.auth.us-west-2.amazoncognito.com"
        assert parsed.path == "/oauth2/authorize"
        assert params["response_type"] == ["code"]
        assert params["client_id"] == ["test-client-id"]
        assert params["redirect_uri"] == ["https://example.com/callback"]
        assert params["scope"] == ["openid email profile"]
        assert "state" in params
        assert "nonce" in params

    def test_get_authorization_url_with_custom_state(self):
        """Test authorization URL generation with custom state."""
        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
        )

        auth_url = manager.get_authorization_url(state="custom-state")

        parsed = httpx.URL(auth_url)
        params = parse_qs(
            parsed.query.decode()
            if hasattr(parsed.query, "decode")
            else str(parsed.query)
        )

        assert params["state"] == ["custom-state"]

    @patch("unity_initiator.utils.oauth2_utils.httpx.Client")
    def test_exchange_code_for_token_success(self, mock_client_class):
        """Test successful token exchange."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status.return_value = None

        # Mock client
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
        )

        result = manager.exchange_code_for_token("test-auth-code")

        # Verify client was called correctly
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert (
            call_args[0][0]
            == "https://test.auth.us-west-2.amazoncognito.com/oauth2/token"
        )

        # Verify form data
        form_data = call_args[1]["data"]
        assert form_data["grant_type"] == "authorization_code"
        assert form_data["client_id"] == "test-client-id"
        assert form_data["code"] == "test-auth-code"
        assert form_data["redirect_uri"] == "https://example.com/callback"

        # Verify headers
        headers = call_args[1]["headers"]
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"

        # Verify result
        assert result["access_token"] == "test-access-token"
        assert result["refresh_token"] == "test-refresh-token"
        assert result["expires_in"] == 3600

        # Verify tokens were stored
        assert manager._access_token == "test-access-token"
        assert manager._refresh_token == "test-refresh-token"
        assert manager._token_expires_at is not None

    @patch("unity_initiator.utils.oauth2_utils.httpx.Client")
    def test_exchange_code_for_token_http_error(self, mock_client_class):
        """Test token exchange with HTTP error."""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.text = "Invalid authorization code"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=Mock(), response=mock_response
        )

        # Mock client
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
        )

        with pytest.raises(httpx.HTTPStatusError):
            manager.exchange_code_for_token("invalid-code")

    @patch("unity_initiator.utils.oauth2_utils.httpx.Client")
    def test_refresh_access_token_success(self, mock_client_class):
        """Test successful token refresh."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status.return_value = None

        # Mock client
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
        )

        # Set up existing refresh token
        manager._refresh_token = "existing-refresh-token"

        result = manager.refresh_access_token()

        # Verify client was called correctly
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        # Verify form data
        form_data = call_args[1]["data"]
        assert form_data["grant_type"] == "refresh_token"
        assert form_data["client_id"] == "test-client-id"
        assert form_data["refresh_token"] == "existing-refresh-token"

        # Verify result
        assert result == "new-access-token"
        assert manager._access_token == "new-access-token"

    def test_refresh_access_token_no_refresh_token(self):
        """Test token refresh when no refresh token is available."""
        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
        )

        result = manager.refresh_access_token()
        assert result is None

    def test_get_valid_token_with_valid_token(self):
        """Test getting valid token when token is still valid."""
        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
        )

        # Set up valid token
        manager._access_token = "valid-token"
        manager._token_expires_at = time.time() + 3600  # Expires in 1 hour

        result = manager.get_valid_token()
        assert result == "valid-token"

    @patch.object(OAuth2Manager, "refresh_access_token")
    def test_get_valid_token_with_expired_token(self, mock_refresh):
        """Test getting valid token when token is expired."""
        mock_refresh.return_value = "refreshed-token"

        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
        )

        # Set up expired token
        manager._access_token = "expired-token"
        manager._refresh_token = "refresh-token"
        manager._token_expires_at = time.time() - 60  # Expired 1 minute ago

        result = manager.get_valid_token()

        assert result == "refreshed-token"
        mock_refresh.assert_called_once()

    def test_get_valid_token_no_tokens(self):
        """Test getting valid token when no tokens are available."""
        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
        )

        result = manager.get_valid_token()
        assert result is None

    def test_clear_tokens(self):
        """Test clearing stored tokens."""
        manager = OAuth2Manager(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-client-id",
            redirect_uri="https://example.com/callback",
        )

        # Set up tokens
        manager._access_token = "test-token"
        manager._refresh_token = "test-refresh"
        manager._token_expires_at = time.time() + 3600

        manager.clear_tokens()

        assert manager._access_token is None
        assert manager._refresh_token is None
        assert manager._token_expires_at is None


class TestExtractAuthorizationCodeFromUrl:
    """Test extract_authorization_code_from_url function."""

    def test_extract_authorization_code_success(self):
        """Test successful authorization code extraction."""
        url = "https://example.com/callback?code=test-auth-code&state=test-state"

        result = extract_authorization_code_from_url(url)

        assert result == "test-auth-code"

    def test_extract_authorization_code_with_error(self):
        """Test authorization code extraction with OAuth2 error."""
        url = "https://example.com/callback?error=access_denied&error_description=User+cancelled+authorization"

        result = extract_authorization_code_from_url(url)

        assert result is None

    def test_extract_authorization_code_no_code(self):
        """Test authorization code extraction when no code is present."""
        url = "https://example.com/callback?state=test-state"

        result = extract_authorization_code_from_url(url)

        assert result is None

    def test_extract_authorization_code_invalid_url(self):
        """Test authorization code extraction with invalid URL."""
        url = "not-a-valid-url"

        result = extract_authorization_code_from_url(url)

        assert result is None


class TestGetOAuth2Headers:
    """Test get_oauth2_headers function."""

    def test_get_oauth2_headers(self):
        """Test OAuth2 headers generation."""
        token = "test-access-token"

        headers = get_oauth2_headers(token)

        expected_headers = {
            "Authorization": "Bearer test-access-token",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        assert headers == expected_headers
