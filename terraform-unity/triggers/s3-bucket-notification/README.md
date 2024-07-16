# s3_bucket_notification

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.4.6 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | >=5.50.0 |
| <a name="requirement_local"></a> [local](#requirement\_local) | >=2.5.1 |
| <a name="requirement_null"></a> [null](#requirement\_null) | >=3.2.2 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 5.51.1 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_s3_bucket_notification.isl_bucket_notification](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_notification) | resource |
| [aws_sns_topic_policy.isl_event_topic_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic_policy) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_initiator_topic_arn"></a> [initiator\_topic\_arn](#input\_initiator\_topic\_arn) | The ARN of the initiator SNS topic to publish S3 events to | `string` | n/a | yes |
| <a name="input_isl_bucket"></a> [isl\_bucket](#input\_isl\_bucket) | The S3 bucket to use as the ISL (incoming staging location) | `string` | n/a | yes |
| <a name="input_isl_bucket_prefix"></a> [isl\_bucket\_prefix](#input\_isl\_bucket\_prefix) | The prefix in the S3 bucket to use as the ISL (incoming staging location) | `string` | n/a | yes |

## Outputs

No outputs.
<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
