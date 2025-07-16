import uuid
from datetime import datetime
from typing import Optional

import httpx

from ..utils.auth_utils import TokenManager, get_auth_headers
from ..utils.logger import logger
from ..utils.oauth2_utils import OAuth2Manager
from .base import Action

__all__ = ["SubmitDagByID"]


class SubmitDagByID(Action):
    def __init__(self, payload, payload_info, params):
        super().__init__(payload, payload_info, params)
        logger.info("instantiated %s", __class__.__name__)
        self._token_manager: Optional[TokenManager] = None
        self._oauth2_manager: Optional[OAuth2Manager] = None

    def _get_auth_token(self) -> Optional[str]:
        """
        Get authentication token based on available parameters.
        Supports direct token, Cognito token fetching, and OAuth2 authentication.
        """
        # Check if token is directly provided
        if "airflow_token" in self._params:
            return self._params["airflow_token"]

        # Check if OAuth2 credentials are provided
        oauth2_params = [
            "oauth2_cognito_domain",
            "oauth2_client_id",
            "oauth2_redirect_uri",
        ]
        if all(param in self._params for param in oauth2_params):
            # Initialize or use existing OAuth2 manager
            if not self._oauth2_manager:
                self._oauth2_manager = OAuth2Manager(
                    cognito_domain=self._params["oauth2_cognito_domain"],
                    client_id=self._params["oauth2_client_id"],
                    redirect_uri=self._params["oauth2_redirect_uri"],
                    scope=self._params.get("oauth2_scope", "openid email profile"),
                    region=self._params.get("oauth2_region", "us-west-2"),
                    verify_ssl=self._params.get("oauth2_verify_ssl", True),
                )

            # Get valid OAuth2 token (automatically refreshes if needed)
            return self._oauth2_manager.get_valid_token()

        # Check if Cognito credentials are provided for token fetching
        cognito_params = ["unity_username", "unity_password", "unity_client_id"]

        if all(param in self._params for param in cognito_params):
            # Initialize or use existing token manager
            if not self._token_manager:
                region = self._params.get("unity_region", "us-west-2")
                self._token_manager = TokenManager(
                    username=self._params["unity_username"],
                    password=self._params["unity_password"],
                    client_id=self._params["unity_client_id"],
                    region=region,
                )

            # Get valid token (automatically refreshes if needed)
            return self._token_manager.get_valid_token()

        return None

    def execute(self):
        # TODO: flesh this method out completely in accordance with:
        # https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/post_dag_run
        logger.debug("executing execute in %s", __class__.__name__)
        url = f"{self._params['airflow_base_api_endpoint']}/dags/{self._params['dag_id']}/dagRuns"
        logger.info("url: %s", url)

        dag_run_id = str(uuid.uuid4())
        logical_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Determine authentication method
        token = self._get_auth_token()

        if token:
            # Use Bearer token authentication
            headers = get_auth_headers(auth_type="bearer", token=token)
            auth = None
        elif "airflow_username" in self._params and "airflow_password" in self._params:
            # Use basic authentication
            headers = get_auth_headers(
                auth_type="basic",
                username=self._params["airflow_username"],
                password=self._params["airflow_password"],
            )
            auth = None
        else:
            # No authentication provided
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            auth = None
            logger.warning("No authentication credentials provided")

        body = {
            "dag_run_id": dag_run_id,
            "logical_date": logical_date,
            "conf": {
                "payload": self._payload,
                "payload_info": self._payload_info,
                "on_success": self._params.get("on_success"),
            },
            "note": "",
        }

        response = httpx.post(
            url, auth=auth, headers=headers, json=body, verify=False
        )  # nosec

        if response.status_code in (200, 201):
            success = True
            resp = response.json()
            logger.info(
                "Successfully triggered Airflow DAG %s: %s",
                self._params["dag_id"],
                resp,
            )
        else:
            success = False
            resp = response.text
            logger.info(
                "Failed to trigger Airflow DAG %s: %s", self._params["dag_id"], resp
            )
        return {"success": success, "response": resp}
