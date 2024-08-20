data "aws_caller_identity" "current" {}

data "aws_iam_policy" "mcp_operator_policy" {
  name = "mcp-tenantOperator-AMI-APIG"
}

data "archive_file" "evaluator_lambda_artifact" {
  type        = "zip"
  output_path = "${path.root}/.archive_files/${var.evaluator_name}-evaluator_lambda.zip"

  source {
    filename = "lambda_function.py"
    content  = <<CODE
import time
import os
import binascii
import json

import boto3


def generate_segment_id():
    return binascii.b2a_hex(os.urandom(8)).decode()

def generate_trace_id(start_time):
    return "1-{}-{}".format(hex(int(start_time))[2:], binascii.hexlify(os.urandom(12)).decode('utf-8'))

def lambda_handler(event, context):
    print(f"event: {json.dumps(event, indent=2, sort_keys=True)}")
    print(f"context: {context}")

    client = boto3.client("xray")

    for rec in event.get("Records", []):

        # get trace info from AWSTraceHeader if set otherwise set them by default
        start_time = time.time()
        aws_trace_header = rec.get("attributes", {}).get("AWSTraceHeader", None)
        if aws_trace_header is None:
            trace_id = generate_trace_id(start_time)
            segment_id = generate_segment_id()
        else:
            d = { k:v for k,v in [i.split("=") for i in d.split(";")]}
            trace_id = d.get("Root", generate_trace_id(start_time))
            segment_id = d.get("Parent", generate_segment_id())

        # Implement your adaptation-specific evaluator code here and return
        # True if it successfully evaluates. False otherwise.

        # write trace
        client.put_trace_segments(
            TraceSegmentDocuments=[
                json.dumps(
                    {
                        "name": context.function_name,
                        "id": segment_id,
                        "start_time": start_time,
                        "trace_id": trace_id,
                        "end_time": time.time(),
                    }
                )
            ]
        )

    return { "success": True }
CODE
  }
}
