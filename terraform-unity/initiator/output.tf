output "initiator_topic_arn" {
  description = "The ARN of the initiator SNS topic"
  value       = aws_sns_topic.initiator_topic.arn
}

output "initiator_lambda_arn" {
  description = "The ARN of the initiator lambda function"
  value       = aws_lambda_function.initiator_lambda.arn
}
