variable "tags" {
  description = "AWS Tags"
  type        = map(string)
}

variable "deployment_name" {
  description = "The deployment name"
  type        = string
}

variable "project" {
  description = "The unity project its installed into"
  type        = string
  default     = "uod"
}

variable "venue" {
  description = "The unity venue its installed into"
  type        = string
  default     = "dev"
}

variable "initiator_topic_arn" {
  description = "The ARN of the initiator SNS topic to publish S3 events to"
  type        = string
}
