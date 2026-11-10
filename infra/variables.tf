variable "region" {
  description = "Region where the resources are created"
  type        = string
  default     = "cn-north-4"
}

variable "app_name" {
  description = "Prefix used for all resource names"
  type        = string
  default     = "upload-content-check"
}

variable "obs_bucket_name" {
  description = "Globally unique bucket name; leave empty to derive one from the app name and region"
  type        = string
  default     = ""
}

variable "function_runtime" {
  description = "FunctionGraph Python runtime"
  type        = string
  default     = "Python3.9"
}

variable "function_memory_size" {
  description = "Function memory in MB"
  type        = number
  default     = 512
}

variable "function_timeout" {
  description = "Function timeout in seconds"
  type        = number
  default     = 60
}

variable "preferred_action" {
  description = "Action taken when a rule matches: delete the object, or tag it and keep it"
  type        = string
  default     = "delete"

  validation {
    condition     = contains(["delete", "tag"], var.preferred_action)
    error_message = "preferred_action must be delete or tag."
  }
}

variable "content_prefix" {
  description = "Only objects under this prefix are inspected; empty means the whole bucket"
  type        = string
  default     = ""
}

variable "enable_timer" {
  description = "Create the scheduled review trigger; set false for a lightweight profile"
  type        = bool
  default     = true
}

variable "timer_schedule" {
  description = "Cron expression for the periodic review"
  type        = string
  default     = "0 0 3 * * ?"
}

variable "timer_schedule_type" {
  description = "Schedule expression type"
  type        = string
  default     = "Cron"
}

variable "lts_ttl_in_days" {
  description = "Log retention in days"
  type        = number
  default     = 7
}

variable "service_name" {
  description = "Service label used in structured log lines"
  type        = string
  default     = "upload-content-check"
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}
