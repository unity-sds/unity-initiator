import time
import uuid
from datetime import datetime

import httpx

from ..utils.logger import logger
from .base import Action

__all__ = ["SubmitDagByID"]


def fetch_cognito_token_oauth2(token_url, client_id, client_secret, username, password):
    data = {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
        "scope": "openid",
    }
    response = httpx.post(token_url, data=data)
    response.raise_for_status()
    token_data = response.json()
    return token_data["access_token"], time.time() + token_data.get("expires_in", 3600)


def fetch_cognito_token_initiate_auth(region, client_id, username, password):
    url = f"https://cognito-idp.{region}.amazonaws.com"
    payload = {
        "AuthParameters": {"USERNAME": f"{username}", "PASSWORD": f"{password}"},
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": f"{client_id}",
    }
    headers = {
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
        "Content-Type": "application/x-amz-json-1.1",
    }
    res = httpx.post(url, json=payload, headers=headers).json()
    if "AuthenticationResult" in res:
        access_token = res["AuthenticationResult"]["AccessToken"]
        # Cognito AccessToken is valid for 1 hour by default
        return access_token, time.time() + 3600
    raise RuntimeError(f"Failed to fetch Cognito token: {res}")


class SubmitDagByID(Action):
    def __init__(self, payload, payload_info, params):
        super().__init__(payload, payload_info, params)
        logger.info("instantiated %s", __class__.__name__)

    def execute(self):
        logger.debug("executing execute in %s", __class__.__name__)
        url = f"{self._params['airflow_base_api_endpoint']}/dags/{self._params['dag_id']}/dagRuns"
        logger.info("url: %s", url)
        dag_run_id = str(uuid.uuid4())
        logical_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        auth = None

        # Determine authentication method
        auth_method = self._params.get("auth_method", "basic")
        if auth_method == "bearer":
            # Support both Cognito token fetch methods
            token = self._params.get("bearer_token")
            expiry = self._params.get("bearer_token_expiry", 0)
            now = time.time()
            if not token or now > expiry - 60:  # refresh 1 min before expiry
                token_method = self._params.get("cognito_token_method", "oauth2")
                if token_method == "initiate_auth":
                    logger.info("Fetching Cognito bearer token using InitiateAuth...")
                    token, expiry = fetch_cognito_token_initiate_auth(
                        self._params["cognito_region"],
                        self._params["cognito_client_id"],
                        self._params["cognito_username"],
                        self._params["cognito_password"],
                    )
                else:
                    logger.info(
                        "Fetching Cognito bearer token using OAuth2 password grant..."
                    )
                    token, expiry = fetch_cognito_token_oauth2(
                        self._params["cognito_token_url"],
                        self._params["cognito_client_id"],
                        self._params["cognito_client_secret"],
                        self._params["cognito_username"],
                        self._params["cognito_password"],
                    )
                self._params["bearer_token"] = token
                self._params["bearer_token_expiry"] = expiry
            headers["Authorization"] = f"Bearer {token}"
            auth = None
        else:
            # Default to basic auth
            auth = (self._params["airflow_username"], self._params["airflow_password"])

        body = {
            "dag_run_id": dag_run_id,
            "logical_date": logical_date,
            "conf": {
                "payload": self._payload,
                "payload_info": self._payload_info,
                "on_success": self._params["on_success"],
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
