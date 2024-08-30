output "centralized_log_group_name" {
  description = "The name of the centralized log group"
  value       = aws_cloudwatch_log_group.centralized_log_group.name
}
