# terraform-unity

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.8.2 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | >=5.50.0 |
| <a name="requirement_local"></a> [local](#requirement\_local) | >=2.5.1 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 5.65.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_log_group.centralized_log_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_project"></a> [project](#input\_project) | The unity project its installed into | `string` | `"uod"` | no |
| <a name="input_venue"></a> [venue](#input\_venue) | The unity venue its installed into | `string` | `"dev"` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_centralized_log_group_name"></a> [centralized\_log\_group\_name](#output\_centralized\_log\_group\_name) | The name of the centralized log group |
<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
