resource "null_resource" "build_lambda_package" {
  triggers = { always_run = timestamp() }
  provisioner "local-exec" {
    command = <<EOF
      set -ex
      docker run --rm -v ${path.module}/../../..:/var/task mlupin/docker-lambda:python3.9-build ./terraform-unity/evaluators/${basename(path.cwd)}/build_lambda_package.sh ${var.evaluator_name}
    EOF
  }
}

resource "aws_s3_object" "lambda_package" {
  depends_on = [null_resource.build_lambda_package]
  bucket     = var.code_bucket
  key        = "${var.evaluator_name}-${jsondecode(data.local_file.version.content).version}-lambda.zip"
  source     = "${path.module}/../../../dist/${var.evaluator_name}-${jsondecode(data.local_file.version.content).version}-lambda.zip"
  etag       = filemd5("${path.module}/../../../dist/${var.evaluator_name}-${jsondecode(data.local_file.version.content).version}-lambda.zip")
  tags       = local.tags
}

resource "aws_lambda_function" "evaluator_lambda" {
  depends_on    = [aws_s3_object.lambda_package]
  function_name = local.function_name
  s3_bucket     = var.code_bucket
  s3_key        = "${var.evaluator_name}-${jsondecode(data.local_file.version.content).version}-lambda.zip"
  handler       = "lambda_handler.lambda_handler"
  runtime       = "python3.11"
  role          = aws_iam_role.evaluator_lambda_iam_role.arn
  timeout       = 900
  tags          = local.tags

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format = "Text"
    log_group  = "/unity/log/${var.project}-${var.venue}-initiator-centralized-log-group"
  }
}

resource "aws_lambda_function_event_invoke_config" "invoke_config" {
  function_name                = aws_lambda_function.evaluator_lambda.function_name
  maximum_event_age_in_seconds = 21600
  maximum_retry_attempts       = 0
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
  name           = "${local.function_name}_topic"
  tags           = local.tags
  tracing_config = "Active"
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
