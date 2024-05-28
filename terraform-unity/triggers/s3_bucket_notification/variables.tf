variable "isl_bucket" {
  description = "The S3 bucket to use as the ISL (incoming staging location)"
  type        = string
}

variable "isl_bucket_prefix" {
  description = "The prefix in the S3 bucket to use as the ISL (incoming staging location)"
  type        = string
}

variable "initiator_topic_arn" {
  description = "The ARN of the initiator SNS topic to publish S3 events to"
  type        = string
}
