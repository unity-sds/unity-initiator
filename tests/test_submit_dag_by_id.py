from unittest.mock import Mock, patch

from unity_initiator.actions.submit_dag_by_id import SubmitDagByID


class TestSubmitDagByID:
    """Test SubmitDagByID action."""

    def test_init(self):
        """Test initialization."""
        payload = {"test": "data"}
        payload_info = {"info": "test"}
        params = {"dag_id": "test_dag"}

        action = SubmitDagByID(payload, payload_info, params)

        assert action._payload == payload
        assert action._payload_info == payload_info
        assert action._params == params

    @patch("unity_initiator.actions.submit_dag_by_id.TokenManager")
    def test_get_auth_token_with_cognito_credentials(self, mock_token_manager_class):
        """Test token fetching with Cognito credentials."""
        # Mock TokenManager instance
        mock_manager = Mock()
        mock_manager.get_valid_token.return_value = "test-token-123"
        mock_token_manager_class.return_value = mock_manager

        params = {
            "unity_username": "testuser",
            "unity_password": "testpass",
            "unity_client_id": "test-client-id",
        }

        action = SubmitDagByID({}, {}, params)
        token = action._get_auth_token()

        assert token == "test-token-123"
        mock_token_manager_class.assert_called_once_with(
            username="testuser",
            password="testpass",
            client_id="test-client-id",
            region="us-west-2",
        )
        mock_manager.get_valid_token.assert_called_once()

    def test_get_auth_token_with_direct_token(self):
        """Test token fetching with direct token."""
        params = {"airflow_token": "direct-token-123"}

        action = SubmitDagByID({}, {}, params)
        token = action._get_auth_token()

        assert token == "direct-token-123"

    def test_get_auth_token_no_credentials(self):
        """Test token fetching with no credentials."""
        params = {}

        action = SubmitDagByID({}, {}, params)
        token = action._get_auth_token()

        assert token is None

    @patch("unity_initiator.actions.submit_dag_by_id.httpx.post")
    @patch("unity_initiator.actions.submit_dag_by_id.get_auth_headers")
    def test_execute_with_bearer_token(self, mock_get_headers, mock_post):
        """Test execution with Bearer token authentication."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"dag_run_id": "test-run"}
        mock_post.return_value = mock_response

        mock_get_headers.return_value = {"Authorization": "Bearer test-token"}

        params = {
            "airflow_base_api_endpoint": "https://airflow.example.com",
            "dag_id": "test_dag",
            "airflow_token": "test-token",
        }

        action = SubmitDagByID({"test": "data"}, {"info": "test"}, params)
        result = action.execute()

        assert result["success"] is True
        assert result["response"]["dag_run_id"] == "test-run"
        mock_get_headers.assert_called_once_with(auth_type="bearer", token="test-token")

    @patch("unity_initiator.actions.submit_dag_by_id.httpx.post")
    @patch("unity_initiator.actions.submit_dag_by_id.get_auth_headers")
    def test_execute_with_basic_auth(self, mock_get_headers, mock_post):
        """Test execution with basic authentication."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"dag_run_id": "test-run"}
        mock_post.return_value = mock_response

        mock_get_headers.return_value = {"Authorization": "Basic dGVzdDp0ZXN0"}

        params = {
            "airflow_base_api_endpoint": "https://airflow.example.com",
            "dag_id": "test_dag",
            "airflow_username": "test",
            "airflow_password": "test",
        }

        action = SubmitDagByID({"test": "data"}, {"info": "test"}, params)
        result = action.execute()

        assert result["success"] is True
        assert result["response"]["dag_run_id"] == "test-run"
        mock_get_headers.assert_called_once_with(
            auth_type="basic", username="test", password="test"
        )

    @patch("unity_initiator.actions.submit_dag_by_id.httpx.post")
    def test_execute_with_failed_response(self, mock_post):
        """Test execution with failed response."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        params = {
            "airflow_base_api_endpoint": "https://airflow.example.com",
            "dag_id": "test_dag",
            "airflow_username": "test",
            "airflow_password": "test",
        }

        action = SubmitDagByID({"test": "data"}, {"info": "test"}, params)
        result = action.execute()

        assert result["success"] is False
        assert result["response"] == "Bad Request"

    @patch("unity_initiator.actions.submit_dag_by_id.OAuth2Manager")
    def test_get_auth_token_with_oauth2_credentials(self, mock_oauth2_manager_class):
        """Test token fetching with OAuth2 credentials."""
        # Mock OAuth2Manager instance
        mock_manager = Mock()
        mock_manager.get_valid_token.return_value = "oauth2-token-123"
        mock_oauth2_manager_class.return_value = mock_manager

        params = {
            "oauth2_cognito_domain": "test.auth.us-west-2.amazoncognito.com",
            "oauth2_client_id": "test-oauth2-client-id",
            "oauth2_redirect_uri": "https://example.com/callback",
            "oauth2_scope": "openid email profile",
            "oauth2_region": "us-west-2",
        }

        action = SubmitDagByID({}, {}, params)
        token = action._get_auth_token()

        assert token == "oauth2-token-123"
        mock_oauth2_manager_class.assert_called_once_with(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-oauth2-client-id",
            redirect_uri="https://example.com/callback",
            scope="openid email profile",
            region="us-west-2",
            verify_ssl=True,
        )
        mock_manager.get_valid_token.assert_called_once()

    @patch("unity_initiator.actions.submit_dag_by_id.OAuth2Manager")
    def test_get_auth_token_oauth2_priority_over_cognito(
        self, mock_oauth2_manager_class
    ):
        """Test that OAuth2 credentials take priority over Cognito credentials."""
        # Mock OAuth2Manager instance
        mock_manager = Mock()
        mock_manager.get_valid_token.return_value = "oauth2-token-123"
        mock_oauth2_manager_class.return_value = mock_manager

        params = {
            # OAuth2 credentials
            "oauth2_cognito_domain": "test.auth.us-west-2.amazoncognito.com",
            "oauth2_client_id": "test-oauth2-client-id",
            "oauth2_redirect_uri": "https://example.com/callback",
            # Cognito credentials (should be ignored)
            "unity_username": "testuser",
            "unity_password": "testpass",
            "unity_client_id": "test-client-id",
        }

        action = SubmitDagByID({}, {}, params)
        token = action._get_auth_token()

        assert token == "oauth2-token-123"
        # OAuth2Manager should be called, not TokenManager
        mock_oauth2_manager_class.assert_called_once()

    @patch("unity_initiator.actions.submit_dag_by_id.OAuth2Manager")
    def test_get_auth_token_with_oauth2_credentials_verify_ssl_false(
        self, mock_oauth2_manager_class
    ):
        """Test token fetching with OAuth2 credentials and verify_ssl=False."""
        # Mock OAuth2Manager instance
        mock_manager = Mock()
        mock_manager.get_valid_token.return_value = "oauth2-token-123"
        mock_oauth2_manager_class.return_value = mock_manager

        params = {
            "oauth2_cognito_domain": "test.auth.us-west-2.amazoncognito.com",
            "oauth2_client_id": "test-oauth2-client-id",
            "oauth2_redirect_uri": "https://example.com/callback",
            "oauth2_scope": "openid email profile",
            "oauth2_region": "us-west-2",
            "oauth2_verify_ssl": False,
        }

        action = SubmitDagByID({}, {}, params)
        token = action._get_auth_token()

        assert token == "oauth2-token-123"
        mock_oauth2_manager_class.assert_called_once_with(
            cognito_domain="test.auth.us-west-2.amazoncognito.com",
            client_id="test-oauth2-client-id",
            redirect_uri="https://example.com/callback",
            scope="openid email profile",
            region="us-west-2",
            verify_ssl=False,
        )
        mock_manager.get_valid_token.assert_called_once()
