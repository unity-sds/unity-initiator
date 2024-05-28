output "lambda_function_arn" {
  description = "The ARN of the Lambda function"
  value       = aws_lambda_function.initiator_lambda.arn
}

output "lambda_function_name" {
  description = "The name of the Lambda function"
  value       = aws_lambda_function.initiator_lambda.function_name
}

output "initiator_queue_arn" {
  description = "The ARN of the initiator SQS queue"
  value       = aws_sqs_queue.initiator_queue.arn
}

output "initiator_topic_arn" {
  description = "The ARN of the initiator SNS topic"
  value       = aws_sns_topic.initiator_topic.arn
}
