import json
import os
from html import unescape
from tempfile import mkstemp

import smart_open
from aws_xray_sdk.core import patch_all, xray_recorder

from ..router import Router
from ..utils.logger import logger

# initialize the AWS X-Ray SDK
patch_all()


ROUTER = None


def lambda_handler_base(event, context):
    """Base lambda handler that instantiates a router, globally, and executes actions for a single payload."""

    logger.info("context: %s", context)

    # TODO: Should use AppConfig. For now, either reading router config body in ROUTER_CFG env variable
    # or from a url in ROUTER_CFG_URL env variable.
    global ROUTER
    if ROUTER is None:
        with xray_recorder.capture("read_router_config"):
            router_cfg = os.environ.get("ROUTER_CFG", "").strip()
            router_cfg_url = os.environ.get("ROUTER_CFG_URL", "").strip()
            if router_cfg == "":
                if router_cfg_url != "":
                    with smart_open.open(router_cfg_url, "r") as f:
                        router_cfg = f.read()
                else:
                    raise RuntimeError(
                        "No router configuration specified via ROUTER_CFG or ROUTER_CFG_URL env variables."
                    )
            fd, router_file = mkstemp(prefix="router_", suffix=".yaml", text=True)
            with os.fdopen(fd, "w") as f:
                f.write(router_cfg)
            ROUTER = Router(router_file)
            os.unlink(router_file)
    with xray_recorder.capture("execute_actions") as subsegment:
        subsegment.put_annotation("payload", event["payload"])
        return ROUTER.execute_actions(event["payload"])


def lambda_handler_multiple_payloads(event, context):
    """Lambda handler that executes actions for a list of event payloads."""

    return [lambda_handler_base(evt, context) for evt in event]


def lambda_handler_initiator(event, context):
    """Lambda handler that executes actions for a list of S3 notification events propagated through SNS->SQS or
    from a scheduled task via EventBridge->Lambda."""

    logger.info("event: %s", json.dumps(event, indent=2))
    payloads = []
    for record in event["Records"]:
        body = json.loads(unescape(record["body"]))
        message = json.loads(body["Message"])

        # TODO: Find cleaner way of parsing payloads from a variety of sources (S3 event notification, EventBridge->Lambda).
        # For now we use brittle assumptions on the payload structure for each of the supported sources.

        if isinstance(message, dict):
            # skip S3 test event
            if message.get("Event", None) == "s3:TestEvent":
                logger.info("Skipped s3:TestEvent")
                continue

            # payload comes from S3 notification
            if "Records" in message:
                for rec in message["Records"]:
                    s3_info = rec["s3"]
                    payloads.append(
                        {
                            "payload": f"s3://{s3_info['bucket']['name']}/{s3_info['object']['key']}"
                        }
                    )
        elif isinstance(message, list):
            # payload comes from EventBridge scheduled task
            payloads.extend(message)
        else:
            payloads.append(message)

    return lambda_handler_multiple_payloads(payloads, context)
