# Object write notifications are delivered through a notification topic.
# The topic is the single entry point for both event sources below.
resource "huaweicloud_smn_topic" "object_events" {
  name                     = "${local.name_prefix}-object-events"
  display_name             = "Object write notifications"
  services_publish_allowed = "cts"
}

# Key operation notifications select object writes in the bucket.
resource "huaweicloud_cts_notification" "object_writes" {
  name           = "${local.name_prefix}-object-writes"
  operation_type = "customized"
  smn_topic      = huaweicloud_smn_topic.object_events.topic_urn

  operations {
    service     = "OBS"
    resource    = "bucket"
    trace_names = ["createObject"]
  }
}

resource "huaweicloud_fgs_trigger" "smn" {
  function_urn = trimsuffix(huaweicloud_fgs_function.checker.urn, ":latest")
  type         = "SMN"

  smn {
    topic_urn = huaweicloud_smn_topic.object_events.topic_urn
  }

  depends_on = [huaweicloud_fgs_function.checker]
}

# A periodic invocation runs the review path without rewriting objects.
# The lightweight profile disables it so only event-driven checks are created.
resource "huaweicloud_fgs_trigger" "timer" {
  count = var.enable_timer ? 1 : 0

  function_urn = trimsuffix(huaweicloud_fgs_function.checker.urn, ":latest")
  type         = "TIMER"

  timer {
    name          = "${local.name_prefix}-review"
    schedule      = var.timer_schedule
    schedule_type = var.timer_schedule_type
  }

  depends_on = [huaweicloud_fgs_function.checker]
}
