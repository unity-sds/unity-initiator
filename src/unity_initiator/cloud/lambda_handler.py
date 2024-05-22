import json
import os
from tempfile import mkstemp

from ..router import Router
from ..utils.logger import logger

ROUTER = None


def lambda_handler_base(event, context):
    """Base lambda handler that instantiates a router, globally, and executes actions for a single payload."""
    logger.info("context: %s", context)

    # TODO: Should use either AppConfig or retrieve router config from S3 location.
    # For now, reading router config body from ROUTER_CFG env variable then writing
    # to local file.
    global ROUTER
    if ROUTER is None:
        router_cfg = os.environ["ROUTER_CFG"]
        fd, router_file = mkstemp(prefix="router_", suffix=".yaml", text=True)
        with os.fdopen(fd, "w") as f:
            f.write(router_cfg)
        ROUTER = Router(router_file)
        os.unlink(router_file)
    return ROUTER.execute_actions(event["payload"])


def lambda_handler_multiple_payloads(event, context):
    """Lambda handler that executes actions for a list of event payloads."""

    return [lambda_handler_base(evt["payload"], context) for evt in event]


def lambda_handler_initiator(event, context):
    """Lambda handler that executes actions for a list of S3 notification events propagated through SNS->SQS."""

    payloads = []
    sqs_messages = event["Messages"]
    for sqs_message in sqs_messages:
        sns_message = json.loads(sqs_message["Body"])
        s3_records = json.loads(sns_message["Message"])
        for s3_record in s3_records:
            payloads.append(
                {
                    "payload": f"s3://{s3_record['s3']['bucket']['name']}/{s3_record['s3']['object']['key']}"
                }
            )
    return lambda_handler_multiple_payloads(payloads, context)
