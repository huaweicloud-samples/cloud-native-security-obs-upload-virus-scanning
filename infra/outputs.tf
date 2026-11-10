output "bucket_name" {
  description = "Bucket holding the objects that are checked"
  value       = huaweicloud_obs_bucket.objects.bucket
}

output "function_name" {
  description = "Name of the content check function"
  value       = huaweicloud_fgs_function.checker.name
}

output "function_urn" {
  description = "URN of the content check function"
  value       = huaweicloud_fgs_function.checker.urn
}

output "topic_urn" {
  description = "URN of the object event topic"
  value       = huaweicloud_smn_topic.object_events.topic_urn
}

output "notification_name" {
  description = "Name of the key operation notification"
  value       = huaweicloud_cts_notification.object_writes.name
}

output "smn_trigger_id" {
  description = "ID of the notification trigger"
  value       = huaweicloud_fgs_trigger.smn.id
}

output "timer_trigger_id" {
  description = "ID of the periodic review trigger, empty in the lightweight profile"
  value       = var.enable_timer ? huaweicloud_fgs_trigger.timer[0].id : ""
}

output "lts_group_id" {
  description = "Log group ID"
  value       = huaweicloud_lts_group.app.id
}

output "lts_stream_id" {
  description = "Log stream ID"
  value       = huaweicloud_lts_stream.app.id
}

output "invoke_command" {
  description = "Command used to invoke the function directly for a manual check"
  value       = "hcloud fgs invoke --function-name ${huaweicloud_fgs_function.checker.name} --body '{}'"
}
