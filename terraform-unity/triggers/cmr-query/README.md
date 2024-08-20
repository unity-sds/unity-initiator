# scheduled_task

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.8.2 |
| <a name="requirement_archive"></a> [archive](#requirement\_archive) | >=2.4.2 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | >=5.50.0 |
| <a name="requirement_local"></a> [local](#requirement\_local) | >=2.5.1 |
| <a name="requirement_null"></a> [null](#requirement\_null) | >=3.2.2 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 5.51.1 |
| <a name="provider_local"></a> [local](#provider\_local) | 2.5.1 |
| <a name="provider_null"></a> [null](#provider\_null) | 3.2.2 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_log_group.cmr_query_lambda_log_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group) | resource |
| [aws_dynamodb_table.cmr_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table) | resource |
| [aws_iam_policy.dynamodb_crud_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_policy.scheduler](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_role.cmr_query_lambda_iam_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role.scheduler](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy_attachment.aws_xray_write_only_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_iam_role_policy_attachment.lambda_base_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_iam_role_policy_attachment.lambda_dynamodb_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_iam_role_policy_attachment.lambda_sns_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_iam_role_policy_attachment.scheduler](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_lambda_function.cmr_query_lambda](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function) | resource |
| [aws_s3_object.lambda_package](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_object) | resource |
| [aws_scheduler_schedule.run_cmr_query](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/scheduler_schedule) | resource |
| [null_resource.build_lambda_package](https://registry.terraform.io/providers/hashicorp/null/latest/docs/resources/resource) | resource |
| [aws_caller_identity.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity) | data source |
| [aws_iam_policy.mcp_operator_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy) | data source |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |
| [local_file.version](https://registry.terraform.io/providers/hashicorp/local/latest/docs/data-sources/file) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_code_bucket"></a> [code\_bucket](#input\_code\_bucket) | The S3 bucket where lambda zip files will be stored and accessed | `string` | n/a | yes |
| <a name="input_concept_id"></a> [concept\_id](#input\_concept\_id) | The concept ID for the data collection: https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#granule-search-by-parameters | `string` | n/a | yes |
| <a name="input_initiator_topic_arn"></a> [initiator\_topic\_arn](#input\_initiator\_topic\_arn) | The ARN of the initiator SNS topic to publish S3 events to | `string` | n/a | yes |
| <a name="input_project"></a> [project](#input\_project) | The unity project its installed into | `string` | `"uod"` | no |
| <a name="input_provider_id"></a> [provider\_id](#input\_provider\_id) | The short name for the data provider: https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#granule-search-by-parameters | `string` | n/a | yes |
| <a name="input_schedule_expression"></a> [schedule\_expression](#input\_schedule\_expression) | The schedule expression to use for executing the CMR query lambda: https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html | `string` | `"rate(5 minutes)"` | no |
| <a name="input_seconds_back"></a> [seconds\_back](#input\_seconds\_back) | Number of seconds back from the current time. Used to create a start and end timerange for a temporal search on granules in the data collection. | `number` | n/a | yes |
| <a name="input_venue"></a> [venue](#input\_venue) | The unity venue its installed into | `string` | `"dev"` | no |

## Outputs

No outputs.
<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
