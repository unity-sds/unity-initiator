resource "null_resource" "build_lambda_package" {
  triggers = { always_run = timestamp() }
  provisioner "local-exec" {
    command = <<EOF
      set -ex
      docker run --rm -v ${path.module}/../../..:/var/task mlupin/docker-lambda:python3.9-build ./scripts/build_cmr_query_lambda_package.sh
    EOF
  }
}

resource "aws_s3_object" "lambda_package" {
  depends_on = [null_resource.build_lambda_package]
  bucket     = var.code_bucket
  key        = "cmr_query-${jsondecode(data.local_file.version.content).version}-lambda.zip"
  source     = "${path.module}/../../../dist/cmr_query-${jsondecode(data.local_file.version.content).version}-lambda.zip"
  etag       = filemd5("${path.module}/../../../dist/cmr_query-${jsondecode(data.local_file.version.content).version}-lambda.zip")
  tags       = local.tags
}

resource "aws_iam_role" "cmr_query_lambda_iam_role" {
  name = "${var.project}-${var.venue}-${var.deployment_name}-cmr_query_lambda_iam_role"

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
  tags                 = local.tags
}

resource "aws_iam_role_policy_attachment" "lambda_sns_policy_attachment" {
  role       = aws_iam_role.cmr_query_lambda_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSNSFullAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_base_policy_attachment" {
  role       = aws_iam_role.cmr_query_lambda_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "cmr_query_lambda" {
  depends_on    = [aws_s3_object.lambda_package]
  function_name = "${var.project}-${var.venue}-${var.deployment_name}-cmr_query"
  s3_bucket     = var.code_bucket
  s3_key        = "cmr_query-${jsondecode(data.local_file.version.content).version}-lambda.zip"
  handler       = "lambda_handler.lambda_handler"
  runtime       = "python3.11"
  role          = aws_iam_role.cmr_query_lambda_iam_role.arn
  timeout       = 900

  environment {
    variables = {
      INITIATOR_TOPIC_ARN = var.initiator_topic_arn
    }
  }
  tags = local.tags
}

resource "aws_iam_role" "scheduler" {
  name = "${var.project}-${var.venue}-${var.deployment_name}-cron-scheduler-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = ["scheduler.amazonaws.com"]
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  permissions_boundary = data.aws_iam_policy.mcp_operator_policy.arn
  tags                 = local.tags
}

resource "aws_iam_policy" "scheduler" {
  name = "${var.project}-${var.venue}-${var.deployment_name}-cron-scheduler-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # allow scheduler to execute the task
        Effect = "Allow",
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.cmr_query_lambda.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "scheduler" {
  policy_arn = aws_iam_policy.scheduler.arn
  role       = aws_iam_role.scheduler.name
}

resource "aws_scheduler_schedule" "run_cmr_query" {
  name                = "${var.project}-${var.venue}-${var.deployment_name}-run_cmr_query"
  schedule_expression = "rate(1 minute)"
  flexible_time_window {
    mode = "OFF"
  }
  target {
    arn      = aws_lambda_function.cmr_query_lambda.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}
