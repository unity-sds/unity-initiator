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
  default     = "UnknownProject"
}

variable "venue" {
  description = "The unity venue its installed into"
  type        = string
  default     = "UnknownVenue"
}