import time
from unittest.mock import MagicMock, patch

import pytest

from src.unity_initiator.actions.submit_dag_by_id import SubmitDagByID

BASIC_PARAMS = {
    "dag_id": "test_dag",
    "airflow_base_api_endpoint": "https://airflow.example.com/api/v1",
    "auth_method": "basic",
    "airflow_username": "user",
    "airflow_password": "pass",
    "on_success": None,
}

OAUTH2_PARAMS = {
    "dag_id": "test_dag",
    "airflow_base_api_endpoint": "https://airflow.example.com/api/v1",
    "auth_method": "bearer",
    "cognito_token_method": "oauth2",
    "cognito_token_url": "https://cognito-domain/oauth2/token",
    "cognito_client_id": "cid",
    "cognito_client_secret": "csecret",
    "cognito_username": "uname",
    "cognito_password": "pword",
    "on_success": None,
}

INITIATE_AUTH_PARAMS = {
    "dag_id": "test_dag",
    "airflow_base_api_endpoint": "https://airflow.example.com/api/v1",
    "auth_method": "bearer",
    "cognito_token_method": "initiate_auth",
    "cognito_region": "us-west-2",
    "cognito_client_id": "cid",
    "cognito_username": "uname",
    "cognito_password": "pword",
    "on_success": None,
}


@pytest.mark.parametrize(
    "params,expected_auth,expected_header",
    [
        (BASIC_PARAMS, ("user", "pass"), None),
        (OAUTH2_PARAMS, None, "Bearer fake-oauth2-token"),
        (INITIATE_AUTH_PARAMS, None, "Bearer fake-initiate-token"),
    ],
)
def test_submit_dag_by_id_auth_modes(params, expected_auth, expected_header):
    """
    Example YAML for basic auth:
    ---
    submit_dag_by_id_action:
      name: submit_dag_by_id
      params:
        dag_id: test_dag
        airflow_base_api_endpoint: https://airflow.example.com/api/v1
        auth_method: basic
        airflow_username: user
        airflow_password: pass

    Example YAML for bearer (oauth2):
    ---
    submit_dag_by_id_action:
      name: submit_dag_by_id
      params:
        dag_id: test_dag
        airflow_base_api_endpoint: https://airflow.example.com/api/v1
        auth_method: bearer
        cognito_token_method: oauth2
        cognito_token_url: https://cognito-domain/oauth2/token
        cognito_client_id: cid
        cognito_client_secret: csecret
        cognito_username: uname
        cognito_password: pword

    Example YAML for bearer (initiate_auth):
    ---
    submit_dag_by_id_action:
      name: submit_dag_by_id
      params:
        dag_id: test_dag
        airflow_base_api_endpoint: https://airflow.example.com/api/v1
        auth_method: bearer
        cognito_token_method: initiate_auth
        cognito_region: us-west-2
        cognito_client_id: cid
        cognito_username: uname
        cognito_password: pword
    """
    payload = {"foo": "bar"}
    payload_info = {"meta": "data"}

    # Patch httpx.post for both DAG trigger and token fetch
    with patch("src.unity_initiator.actions.submit_dag_by_id.httpx.post") as mock_post:
        # Mock token fetch
        if params.get("auth_method") == "bearer":
            if params.get("cognito_token_method") == "oauth2":
                # First call: token fetch
                mock_post.side_effect = [
                    MagicMock(
                        json=lambda: {
                            "access_token": "fake-oauth2-token",
                            "expires_in": 3600,
                        },
                        status_code=200,
                    ),
                    MagicMock(json=lambda: {"result": "ok"}, status_code=200),
                ]
            else:
                # First call: token fetch
                mock_post.side_effect = [
                    MagicMock(
                        json=lambda: {
                            "AuthenticationResult": {
                                "AccessToken": "fake-initiate-token"
                            }
                        },
                        status_code=200,
                    ),
                    MagicMock(json=lambda: {"result": "ok"}, status_code=200),
                ]
        else:
            mock_post.return_value = MagicMock(
                json=lambda: {"result": "ok"}, status_code=200
            )

        action = SubmitDagByID(payload, payload_info, params.copy())
        result = action.execute()
        assert result["success"]
        # Check correct auth or header used
        if expected_auth:
            args, kwargs = mock_post.call_args
            assert kwargs["auth"] == expected_auth
        if expected_header:
            # The second call is the DAG trigger
            _, kwargs = mock_post.call_args
            assert kwargs["headers"]["Authorization"] == expected_header


def test_token_refresh_on_expiry():
    params = OAUTH2_PARAMS.copy()
    params["bearer_token"] = "expired-token"
    params["bearer_token_expiry"] = time.time() - 10  # expired
    payload = {}
    payload_info = {}
    with patch("src.unity_initiator.actions.submit_dag_by_id.httpx.post") as mock_post:
        mock_post.side_effect = [
            MagicMock(
                json=lambda: {"access_token": "new-token", "expires_in": 3600},
                status_code=200,
            ),
            MagicMock(json=lambda: {"result": "ok"}, status_code=200),
        ]
        action = SubmitDagByID(payload, payload_info, params)
        result = action.execute()
        assert result["success"]
        # Should use new token
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer new-token"


def test_missing_required_params():
    params = BASIC_PARAMS.copy()
    del params["airflow_username"]
    payload = {}
    payload_info = {}
    with pytest.raises(KeyError):
        SubmitDagByID(payload, payload_info, params).execute()
