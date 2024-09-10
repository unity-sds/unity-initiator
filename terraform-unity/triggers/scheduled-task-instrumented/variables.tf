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

variable "code_bucket" {
  description = "The S3 bucket where lambda zip files will be stored and accessed"
  type        = string
}

variable "initiator_topic_arn" {
  description = "The ARN of the initiator SNS topic to publish S3 events to"
  type        = string
}
