import json

import boto3

from ..utils.logger import logger
from .base import Action

__all__ = ["SubmitToSNSTopic"]


class SubmitToSNSTopic(Action):

    def __init__(self, payload, payload_info, params):
        super().__init__(payload, payload_info, params)
        self._topic_arn = self._params.get("topic_arn", None)
        if self._topic_arn is None:
            raise NotImplementedError(
                "Implicit resolution of topic ARN not yet implemented."
            )
        logger.info("instantiated %s", __class__.__name__)

    @property
    def topic_arn(self):
        return self._topic_arn

    def execute(self):
        logger.debug("executed execute in %s", __class__.__name__)
        client = boto3.client("sns")
        resp = client.publish(
            TopicArn=self._topic_arn,
            Message=json.dumps(
                {
                    "payload": self._payload,
                    "payload_info": self._payload_info,
                }
            ),
        )
        return {
            "success": True,
            "response": resp,
        }
