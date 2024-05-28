variable "tags" {
  description = "AWS Tags"
  type        = map(string)
}

variable "evaluator_name" {
  description = "The evaluator name"
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
