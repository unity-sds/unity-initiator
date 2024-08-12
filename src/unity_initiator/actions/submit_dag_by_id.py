import uuid
from datetime import datetime

import httpx

from ..utils.logger import logger
from .base import Action

__all__ = ["SubmitDagByID"]


class SubmitDagByID(Action):
    def __init__(self, payload, payload_info, params):
        super().__init__(payload, payload_info, params)
        logger.info("instantiated %s", __class__.__name__)

    def execute(self):
        # TODO: flesh this method out completely in accordance with:
        # https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/post_dag_run
        logger.debug("executing execute in %s", __class__.__name__)
        url = f"{self._params['airflow_base_api_endpoint']}/dags/{self._params['dag_id']}/dagRuns"
        logger.info("url: %s", url)
        dag_run_id = str(uuid.uuid4())
        logical_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
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
