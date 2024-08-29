resource "null_resource" "build_lambda_package" {
  triggers = { always_run = timestamp() }
  provisioner "local-exec" {
    command = <<EOF
      set -ex
      docker run --rm -v ${path.module}/../../..:/var/task mlupin/docker-lambda:python3.9-build ./scripts/build_scheduled_task_lambda_package.sh
    EOF
  }
}

resource "aws_s3_object" "lambda_package" {
  depends_on = [null_resource.build_lambda_package]
  bucket     = var.code_bucket
  key        = "scheduled_task-${jsondecode(data.local_file.version.content).version}-lambda.zip"
  source     = "${path.module}/../../../dist/scheduled_task-${jsondecode(data.local_file.version.content).version}-lambda.zip"
  etag       = filemd5("${path.module}/../../../dist/scheduled_task-${jsondecode(data.local_file.version.content).version}-lambda.zip")
  tags       = local.tags
}

resource "aws_iam_role" "scheduled_task_lambda_iam_role" {
  name = "${local.function_name}_lambda_iam_role"

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
  role       = aws_iam_role.scheduled_task_lambda_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSNSFullAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_base_policy_attachment" {
  role       = aws_iam_role.scheduled_task_lambda_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "aws_xray_write_only_access" {
  role       = aws_iam_role.scheduled_task_lambda_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_lambda_function" "scheduled_task_lambda" {
  depends_on    = [aws_s3_object.lambda_package, aws_cloudwatch_log_group.scheduled_task_lambda_log_group]
  function_name = local.function_name
  s3_bucket     = var.code_bucket
  s3_key        = "scheduled_task-${jsondecode(data.local_file.version.content).version}-lambda.zip"
  handler       = "lambda_handler.lambda_handler"
  runtime       = "python3.11"
  role          = aws_iam_role.scheduled_task_lambda_iam_role.arn
  timeout       = 900

  environment {
    variables = {
      INITIATOR_TOPIC_ARN = var.initiator_topic_arn
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "scheduled_task_lambda_log_group" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 14
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
        Resource = aws_lambda_function.scheduled_task_lambda.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "scheduler" {
  policy_arn = aws_iam_policy.scheduler.arn
  role       = aws_iam_role.scheduler.name
}

resource "aws_scheduler_schedule" "run_scheduled_task" {
  name                = "${var.project}-${var.venue}-${var.deployment_name}-run_scheduled_task"
  schedule_expression = "rate(1 minute)"
  flexible_time_window {
    mode = "OFF"
  }
  target {
    arn      = aws_lambda_function.scheduled_task_lambda.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}
