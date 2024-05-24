data "aws_iam_policy" "mcp_operator_policy" {
  name = "mcp-tenantOperator-AMI-APIG"
}

resource "aws_iam_role" "lambda_iam_role" {
  name = "initiator_lambda_iam_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
      },
    ],
  })
  permissions_boundary = data.aws_iam_policy.mcp_operator_policy.arn
}

data "archive_file" "test_lambda_artifact" {
  type        = "zip"
  output_path = "${path.root}/.archive_files/test_lambda.zip"

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

# setup the actual lambda resource
resource "aws_lambda_function" "test_lambda" {
  lifecycle {
    # make sure tf doesn't overwrite deployed code once we start deploying
    ignore_changes = [
      filename,
      source_code_hash,
    ]
  }

  function_name = "test_lambda"
  role          = aws_iam_role.lambda_iam_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 256

  filename         = "${path.root}/.archive_files/test_lambda.zip"
  source_code_hash = data.archive_file.test_lambda_artifact.output_base64sha256
}