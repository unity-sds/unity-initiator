output "centralized_log_group_arn" {
  description = "The ARN of the centralized log group"
  value       = aws_cloudwatch_log_group.centralized_log_group.arn
}
