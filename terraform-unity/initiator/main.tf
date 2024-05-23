resource "aws_lambda_function" "initiator_lambda" {
  function_name = "${var.deployment_name}-inititator"

  filename = "${path.module}/lambda.zip"
  handler  = "lambda.lambda_handler"
  runtime  = "python3.11"
  role     = aws_iam_role.initiator_lambda_iam_role.arn

  environment {
    variables = {
      ROUTER_CFG_URL = "s3://test_bucket/test_router.yaml"
    }
  }

  vpc_config {
    subnet_ids         = local.subnet_ids
    security_group_ids = [aws_security_group.initiator_lambda_sg.id]
  }
  tags = var.tags
}

resource "aws_security_group" "initiator_lambda_sg" {
  name        = "${var.deployment_name}-initiator_lambda_sg"
  description = "Security group for the initiator lambda service"
  vpc_id      = data.aws_ssm_parameter.vpc_id.value

  // Inbound rules
  // Example: Allow HTTP and HTTPS
  // ingress {
  //   from_port   = 2049
  //   to_port     = 2049
  //   protocol    = "tcp"
  //   cidr_blocks = ["0.0.0.0/0"]
  // }

  // Outbound rules
  // Example: Allow all outbound traffic
  // egress {
  //   from_port   = 0
  //   to_port     = 0
  //   protocol    = "-1"
  //   cidr_blocks = ["0.0.0.0/0"]
  // }

  tags = var.tags
}


resource "aws_iam_role" "initiator_lambda_iam_role" {
  name = "${var.deployment_name}-initiator_lambda_iam_role"

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

resource "aws_iam_policy" "initiator_lambda_policy" {
  name        = "${var.deployment_name}-initiator_lambda_policy"
  description = "A policy for the Lambda function to access S3"

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
      }
    ]
  })

}

resource "aws_iam_role_policy_attachment" "lambda_base_policy_attachment" {
  role       = aws_iam_role.initiator_lambda_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.initiator_lambda_iam_role.name
  policy_arn = aws_iam_policy.initiator_lambda_policy.arn
}

resource "aws_ssm_parameter" "initiator_lambda_function_name" {
  name  = "/unity/${var.project}/${var.venue}/od/initiator/lambda-name"
  type  = "String"
  value = aws_lambda_function.initiator_lambda.function_name
}


output "lambda_function_arn" {
  description = "The ARN of the Lambda function"
  value       = aws_lambda_function.initiator_lambda.arn
}

output "lambda_function_name" {
  description = "The name of the Lambda function"
  value       = aws_lambda_function.initiator_lambda.function_name
}
