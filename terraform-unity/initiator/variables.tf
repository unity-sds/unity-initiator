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

variable "code_bucket" {
  description = "The S3 bucket where lambda zip files will be stored and accessed"
  type        = string
}

variable "config_bucket" {
  description = "The S3 bucket where router configuration files will be stored and accessed"
  type        = string
}