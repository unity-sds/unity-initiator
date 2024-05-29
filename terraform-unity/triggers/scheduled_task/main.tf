resource "aws_iam_role" "scheduled_task_lambda_iam_role" {
  name = "${var.project}-${var.venue}-${var.deployment_name}-scheduled_task_lambda_iam_role"

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

resource "aws_iam_role_policy_attachment" "lambda_sns_policy_attachment" {
  role       = aws_iam_role.scheduled_task_lambda_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSNSFullAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_base_policy_attachment" {
  role       = aws_iam_role.scheduled_task_lambda_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "scheduled_task_lambda" {
  filename         = data.archive_file.lambda_zip_inline.output_path
  source_code_hash = data.archive_file.lambda_zip_inline.output_base64sha256
  function_name    = "${var.project}-${var.venue}-${var.deployment_name}-scheduled_task"
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  role             = aws_iam_role.scheduled_task_lambda_iam_role.arn
  timeout          = 900

  environment {
    variables = {
      INITIATOR_TOPIC_ARN = var.initiator_topic_arn
    }
  }
  tags = var.tags
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