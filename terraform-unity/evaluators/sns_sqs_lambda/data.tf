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
def lambda_handler(event, context):
    print(f"event: {event}")
    print(f"context: {context}")

    # implement your adaptation-specific evaluator code here and return
    # True if it successfully evaluates. False otherwise.

    return { "success": True }
CODE
  }
}
