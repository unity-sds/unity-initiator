output "initiator_topic_arn" {
  description = "The ARN of the initiator SNS topic"
  value       = aws_sns_topic.initiator_topic.arn
}
