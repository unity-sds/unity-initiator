data "aws_caller_identity" "current" {}

data "aws_iam_policy" "mcp_operator_policy" {
  name = "mcp-tenantOperator-AMI-APIG"
}

data "archive_file" "evaluator_lambda_artifact" {
  type        = "zip"
  output_path = "${path.root}/.archive_files/${var.evaluator_name}-evaluator_lambda.zip"

  # fingerprinter
  source {
    filename = "lambda_function.py"
    content  = <<CODE
def lambda_handler(event, context):
    print(f"event: {event}")
    print(f"context: {context}")
    return { "success": True }
CODE
  }
}
