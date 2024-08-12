import httpx

from ..utils.logger import logger
from .base import Action

__all__ = ["SubmitOgcProcessExecution"]


class SubmitOgcProcessExecution(Action):
    def __init__(self, payload, payload_info, params):
        super().__init__(payload, payload_info, params)
        logger.info("instantiated %s", __class__.__name__)

    def execute(self):
        logger.debug("executing execute in %s", __class__.__name__)
        url = f"{self._params['ogc_processes_base_api_endpoint']}/processes/{self._params['process_id']}/execution"
        logger.info("url: %s", url)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        # body = {
        #     "inputs": self._params["execution_inputs"],
        #     "outputs": self._params["execution_outputs"],
        #     "subscriber": self._params["execution_subscriber"],
        # }
        body = {
            "inputs": {
                "payload": self._payload,
                "payload_info": self._payload_info,
                "on_success": self._params["on_success"],
            },
            "outputs": None,
            "subscriber": None,
        }
        response = httpx.post(url, headers=headers, json=body, verify=False)  # nosec
        if response.status_code in (200, 201):
            success = True
            resp = response.json()
            logger.info(
                "Successfully triggered the execution of the OGC Process %s: %s",
                self._params["process_id"],
                resp,
            )
        else:
            success = False
            resp = response.text
            logger.info(
                "Failed to trigger the execution of the OGC Process %s: %s",
                self._params["process_id"],
                resp,
            )
        return {"success": success, "response": resp}
