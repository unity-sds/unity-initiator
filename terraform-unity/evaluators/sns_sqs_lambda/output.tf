output "evaluator_topic_arn" {
  description = "The ARN of the evaluator SNS topic"
  value       = aws_sns_topic.evaluator_topic.arn
}