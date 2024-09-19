import uuid
from datetime import datetime

import httpx

from ..utils.logger import logger
from .base import Action

__all__ = ["SubmitHysdsJob"]


class SubmitHysdsJob(Action):
    def __init__(self, payload, payload_info, params):
        super().__init__(payload, payload_info, params)
        logger.info("instantiated %s", __class__.__name__)

    def execute(self):
        """Submit job to mozart via REST API."""

        # setup url and request body
        url = f"{self._params['mozart_base_api_endpoint']}/api/v0.1/job/submit"
        body = {
            "queue": self._params["queue"],
            "priority": self._params.get("priority", 0),
            "tags": json.dumps(self._params.get("tags", [])),
            "type": self._params["job_spec"],
            "params": json.dumps(job_params),
            "name": f"{self._params['job_spec'].split(':')[0]}-{str(uuid.uuid4())}"
        }

        # build job params
        job_params = {
            "payload": self._payload,
            "payload_info": self._payload_info,
            "on_success": self._params["on_success"],
        }

        # submit job
        logger.info("job URL: %s", url)
        logger.info("job params: %s", json.dumps(body, indent=2, sort_keys=True))
        response = httpx.post(url, data=body, verify=False)  # nosec
        if response.status_code in (200, 201):
            success = True
            resp = response.json()
            logger.info(
                "Successfully submitted HySDS job %s: %s",
                self._params["job_spec"],
                resp,
            )
        else:
            success = False
            resp = response.text
            logger.info(
                "Failed to submit HySDS job %s: %s", self._params["job_spec"], resp
            )
        return {"success": success, "response": resp}
