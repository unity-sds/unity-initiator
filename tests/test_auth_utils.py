import time
from unittest.mock import Mock, patch

from unity_initiator.utils.auth_utils import (
    TokenInfo,
    TokenManager,
    fetch_cognito_token,
    get_auth_headers,
)


class TestAuthUtils:
    """Test authentication utilities."""

    def test_get_auth_headers_basic(self):
        """Test basic authentication headers."""
        headers = get_auth_headers(
            auth_type="basic", username="testuser", password="testpass"
        )

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_get_auth_headers_bearer(self):
        """Test bearer token authentication headers."""
        token = "test-token-123"
        headers = get_auth_headers(auth_type="bearer", token=token)

        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {token}"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_get_auth_headers_no_auth(self):
        """Test headers without authentication."""
        headers = get_auth_headers()

        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    @patch("unity_initiator.utils.auth_utils.httpx.Client")
    def test_fetch_cognito_token_success(self, mock_client_class):
        """Test successful Cognito token fetching."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "AuthenticationResult": {
                "AccessToken": "test-access-token-123",
                "ExpiresIn": 3600,
            }
        }
        mock_response.raise_for_status.return_value = None

        # Mock client context manager
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client_class.return_value.__exit__.return_value = None

        token = fetch_cognito_token(
            username="testuser", password="testpass", client_id="test-client-id"
        )

        assert token == "test-access-token-123"
        mock_client.post.assert_called_once()

    @patch("unity_initiator.utils.auth_utils.httpx.Client")
    def test_fetch_cognito_token_no_auth_result(self, mock_client_class):
        """Test Cognito token fetching with no authentication result."""
        # Mock response without AuthenticationResult
        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid credentials"}
        mock_response.raise_for_status.return_value = None

        # Mock client context manager
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client_class.return_value.__exit__.return_value = None

        token = fetch_cognito_token(
            username="testuser", password="testpass", client_id="test-client-id"
        )

        assert token is None

    @patch("unity_initiator.utils.auth_utils.httpx.Client")
    def test_fetch_cognito_token_http_error(self, mock_client_class):
        """Test Cognito token fetching with HTTP error."""
        # Mock client that raises HTTPStatusError
        mock_client = Mock()
        mock_client.post.side_effect = Exception("HTTP error")
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client_class.return_value.__exit__.return_value = None

        token = fetch_cognito_token(
            username="testuser", password="testpass", client_id="test-client-id"
        )

        assert token is None

    @patch("unity_initiator.utils.auth_utils.httpx.Client")
    def test_fetch_cognito_token_request_error(self, mock_client_class):
        """Test Cognito token fetching with request error."""
        # Mock client that raises RequestError
        mock_client = Mock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client_class.return_value.__exit__.return_value = None

        token = fetch_cognito_token(
            username="testuser", password="testpass", client_id="test-client-id"
        )

        assert token is None


class TestTokenManager:
    """Test TokenManager class."""

    def test_token_manager_init(self):
        """Test TokenManager initialization."""
        manager = TokenManager("user", "pass", "client-id", "us-west-2")

        assert manager.username == "user"
        assert manager.password == "pass"
        assert manager.client_id == "client-id"
        assert manager.region == "us-west-2"
        assert manager._token_cache is None
        assert manager._refresh_buffer == 300

    def test_token_info_dataclass(self):
        """Test TokenInfo dataclass."""
        token_info = TokenInfo(
            access_token="test-token",
            expires_at=time.time() + 3600,
            refresh_token="refresh-token",
        )

        assert token_info.access_token == "test-token"
        assert token_info.expires_at > time.time()
        assert token_info.refresh_token == "refresh-token"

    @patch("unity_initiator.utils.auth_utils.httpx.Client")
    def test_get_valid_token_first_time(self, mock_client_class):
        """Test getting token for the first time."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "AuthenticationResult": {
                "AccessToken": "test-token-123",
                "ExpiresIn": 3600,
                "RefreshToken": "refresh-token-123",
            }
        }
        mock_response.raise_for_status.return_value = None

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client_class.return_value.__exit__.return_value = None

        manager = TokenManager("user", "pass", "client-id")
        token = manager.get_valid_token()

        assert token == "test-token-123"
        assert manager._token_cache is not None
        assert manager._token_cache.access_token == "test-token-123"
        assert manager._token_cache.refresh_token == "refresh-token-123"

    def test_get_valid_token_cached_valid(self):
        """Test getting token when cached token is still valid."""
        # Create a token that expires in 1 hour
        expires_at = time.time() + 3600
        token_info = TokenInfo(
            access_token="cached-token",
            expires_at=expires_at,
            refresh_token="refresh-token",
        )

        manager = TokenManager("user", "pass", "client-id")
        manager._token_cache = token_info

        token = manager.get_valid_token()

        assert token == "cached-token"

    def test_get_valid_token_cached_expired(self):
        """Test getting token when cached token is expired."""
        # Create a token that expired 1 hour ago
        expires_at = time.time() - 3600
        token_info = TokenInfo(
            access_token="expired-token",
            expires_at=expires_at,
            refresh_token="refresh-token",
        )

        manager = TokenManager("user", "pass", "client-id")
        manager._token_cache = token_info

        # Mock the _fetch_new_token method
        with patch.object(manager, "_fetch_new_token", return_value="new-token"):
            token = manager.get_valid_token()

        assert token == "new-token"

    def test_get_valid_token_cached_expiring_soon(self):
        """Test getting token when cached token is expiring soon."""
        # Create a token that expires in 2 minutes (less than 5-minute buffer)
        expires_at = time.time() + 120
        token_info = TokenInfo(
            access_token="expiring-token",
            expires_at=expires_at,
            refresh_token="refresh-token",
        )

        manager = TokenManager("user", "pass", "client-id")
        manager._token_cache = token_info

        # Mock the _fetch_new_token method
        with patch.object(manager, "_fetch_new_token", return_value="new-token"):
            token = manager.get_valid_token()

        assert token == "new-token"

    @patch("unity_initiator.utils.auth_utils.httpx.Client")
    def test_refresh_token_success(self, mock_client_class):
        """Test successful token refresh."""
        # Mock successful refresh response
        mock_response = Mock()
        mock_response.json.return_value = {
            "AuthenticationResult": {
                "AccessToken": "refreshed-token",
                "ExpiresIn": 3600,
            }
        }
        mock_response.raise_for_status.return_value = None

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client_class.return_value.__exit__.return_value = None

        manager = TokenManager("user", "pass", "client-id")
        manager._token_cache = TokenInfo(
            access_token="old-token",
            expires_at=time.time() - 3600,  # Expired
            refresh_token="refresh-token",
        )

        token = manager._refresh_token()

        assert token == "refreshed-token"
        assert manager._token_cache.access_token == "refreshed-token"

    def test_refresh_token_no_refresh_token(self):
        """Test refresh when no refresh token is available."""
        manager = TokenManager("user", "pass", "client-id")
        manager._token_cache = TokenInfo(
            access_token="old-token",
            expires_at=time.time() - 3600,  # Expired
            refresh_token=None,  # No refresh token
        )

        # Mock the _fetch_new_token method
        with patch.object(manager, "_fetch_new_token", return_value="new-token"):
            token = manager._refresh_token()

        assert token == "new-token"

    def test_clear_cache(self):
        """Test clearing the token cache."""
        manager = TokenManager("user", "pass", "client-id")
        manager._token_cache = TokenInfo(
            access_token="test-token",
            expires_at=time.time() + 3600,
            refresh_token="refresh-token",
        )

        manager.clear_cache()

        assert manager._token_cache is None
