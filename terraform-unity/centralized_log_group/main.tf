resource "aws_cloudwatch_log_group" "centralized_log_group" {
  name              = "/unity/log/${local.log_group_name}"
  retention_in_days = 14
  tags              = local.tags
}
