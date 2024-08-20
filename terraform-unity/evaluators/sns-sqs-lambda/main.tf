# setup the actual lambda resource
resource "aws_lambda_function" "evaluator_lambda" {
  lifecycle {
    # make sure tf doesn't overwrite deployed code once we start deploying
    ignore_changes = [
      filename,
      source_code_hash,
    ]
  }

  function_name    = local.function_name
  role             = aws_iam_role.evaluator_lambda_iam_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  timeout          = 900
  filename         = "${path.root}/.archive_files/${var.evaluator_name}-evaluator_lambda.zip"
  source_code_hash = data.archive_file.evaluator_lambda_artifact.output_base64sha256
  tags             = local.tags

  tracing_config {
    mode = "Active"
  }
}

resource "aws_cloudwatch_log_group" "evaluator_lambda_log_group" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 14
}

resource "aws_iam_role" "evaluator_lambda_iam_role" {
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

resource "aws_iam_policy" "evaluator_lambda_policy" {
  name        = "${local.function_name}_lambda_policy"
  description = "A policy for the evaluator lambda function to access S3 and SQS"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "ListObjectsInBucket",
        "Effect" : "Allow",
        "Action" : ["s3:ListBucket"],
        "Resource" : ["arn:aws:s3:::*"]
      },
      {
        "Sid" : "AllObjectActions",
        "Effect" : "Allow",
        "Action" : "s3:*Object",
        "Resource" : ["arn:aws:s3:::*"]
      },
      {
        "Sid" : "AccessInitiatorSQS",
        "Effect" = "Allow"
        "Action" = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ],
        "Resource" = [aws_sqs_queue.evaluator_queue.arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.evaluator_lambda_iam_role.name
  policy_arn = aws_iam_policy.evaluator_lambda_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_base_policy_attachment" {
  role       = aws_iam_role.evaluator_lambda_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "aws_xray_write_only_access" {
  role       = aws_iam_role.evaluator_lambda_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_ssm_parameter" "evaluator_lambda_function_name" {
  name  = "/unity/${var.project}/${var.venue}/od/evaluator/${var.evaluator_name}"
  type  = "String"
  value = aws_lambda_function.evaluator_lambda.function_name
  tags  = local.tags
}


resource "aws_sqs_queue" "evaluator_dead_letter_queue" {
  name                       = "${local.function_name}_dead_letter_queue"
  delay_seconds              = 0
  max_message_size           = 2048
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 0
  visibility_timeout_seconds = 900
  tags                       = local.tags
}

resource "aws_sqs_queue" "evaluator_queue" {
  name                       = "${local.function_name}_queue"
  delay_seconds              = 0
  max_message_size           = 2048
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 10
  visibility_timeout_seconds = 900
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.evaluator_dead_letter_queue.arn
    maxReceiveCount     = 2
  })
  tags = local.tags
}

resource "aws_sns_topic" "evaluator_topic" {
  name = "${local.function_name}_topic"
}

resource "aws_sns_topic_policy" "evaluator_topic_policy" {
  arn = aws_sns_topic.evaluator_topic.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
      }
      Action   = "SNS:Publish"
      Resource = aws_sns_topic.evaluator_topic.arn
    }]
  })
}

resource "aws_sqs_queue_policy" "evaluator_queue_policy" {
  queue_url = aws_sqs_queue.evaluator_queue.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.evaluator_queue.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_sns_topic.evaluator_topic.arn
          }
        }
      },
    ]
  })
}

resource "aws_sns_topic_subscription" "evaluator_subscription" {
  topic_arn = aws_sns_topic.evaluator_topic.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.evaluator_queue.arn
}

resource "aws_lambda_event_source_mapping" "evaluator_queue_event_source_mapping" {
  batch_size       = 10
  enabled          = true
  event_source_arn = aws_sqs_queue.evaluator_queue.arn
  function_name    = aws_lambda_function.evaluator_lambda.arn
}
