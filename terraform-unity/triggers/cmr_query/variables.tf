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

variable "schedule_expression" {
  description = "The schedule expression to use for executing the CMR query lambda: https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html"
  type        = string
  default     = "rate(1 minute)"
}

variable "provider_id" {
  description = "The short name for the data provider: https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#granule-search-by-parameters"
  type        = string
}

variable "concept_id" {
  description = "The concept ID for the data collection: https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#granule-search-by-parameters"
  type        = string
}

variable "seconds_back" {
  description = "Number of seconds back from the current time. Used to create a start and end timerange for a temporal search on granules in the data collection."
  type        = number
}
