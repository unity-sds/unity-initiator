data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

data "aws_iam_policy" "mcp_operator_policy" {
  name = "mcp-tenantOperator-AMI-APIG"
}

data "local_file" "version" {
  filename   = "${path.module}/../../../dist/version.json"
  depends_on = [null_resource.build_lambda_package]
}
