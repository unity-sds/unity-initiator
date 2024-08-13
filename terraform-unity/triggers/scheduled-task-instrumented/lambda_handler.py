import json
import os

import boto3
from aws_xray_sdk.core import patch_all, xray_recorder

patch_all()


INITIATOR_TOPIC_ARN = os.environ["INITIATOR_TOPIC_ARN"]


def lambda_handler(event, context):
    print(f"event: {json.dumps(event, indent=2)}")
    print(f"context: {context}")

    # implement your adaptation-specific trigger code here and submit payloads
    # to the SNS topic as either a list of payloads or a single payload. Below
    # is an example of a single payload.
    # Finally return True if it successful. False otherwise.

    with xray_recorder.capture("publish_url_to_inititator_topic"):
        client = boto3.client("sns")
        res = client.publish(
            TopicArn=INITIATOR_TOPIC_ARN,
            Subject="Scheduled Task",
            Message=json.dumps(
                [
                    {
                        "payload": "s3://bucket/prefix/NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_17_57_57_714280000.vc25"
                    }
                ]
            ),
        )
        return {"success": True, "response": res}
