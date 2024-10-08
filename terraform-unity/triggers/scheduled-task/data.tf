data "aws_iam_policy" "mcp_operator_policy" {
  name = "mcp-tenantOperator-AMI-APIG"
}

data "archive_file" "lambda_zip_inline" {
  type        = "zip"
  output_path = "/tmp/lambda_zip_inline.zip"
  source {
    content  = <<EOF
import os
import json
import boto3

INITIATOR_TOPIC_ARN = os.environ["INITIATOR_TOPIC_ARN"]

def lambda_handler(event, context):
    print(f"event: {json.dumps(event, indent=2)}")
    print(f"context: {context}")

    # implement your adaptation-specific trigger code here and submit payloads
    # to the SNS topic as either a list of payloads or a single payload. Below
    # is an example of a single payload.
    # Finally return True if it successful. False otherwise.

    client = boto3.client("sns")
    res = client.publish(
        TopicArn=INITIATOR_TOPIC_ARN,
        Subject="Scheduled Task",
        Message=json.dumps([{"payload": "s3://bucket/prefix/NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_17_57_57_714280000.vc25"}])
    )
    return {
        "success": True,
        "response": res
    }
EOF
    filename = "lambda_function.py"
  }
}
