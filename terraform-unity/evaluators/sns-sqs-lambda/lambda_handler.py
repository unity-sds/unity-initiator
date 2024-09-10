import json

from aws_xray_sdk.core import patch_all, xray_recorder

from unity_initiator.utils.logger import log_exceptions, logger

patch_all()


def perform_evaluation(event, context):
    logger.info("event: %s", json.dumps(event, indent=2))
    logger.info("context: %s", context)

    # Implement your adaptation-specific evaluator code here and return
    # True if it successfully evaluates. False otherwise.

    return True


@log_exceptions
def lambda_handler(event, context):
    with xray_recorder.capture(context.function_name):
        return {"success": perform_evaluation(event, context)}
