"""Normalise the three event shapes this function can receive."""
import json

WRITE_MARKERS = (
    "createobject", "putobject", "postobject", "copyobject",
    "uploadpart", "completemultipartupload",
)
SCHEDULE_MARKERS = ("timer", "schedule", "cron")


def unwrap(event):
    """Return the inner operational record carried by the event."""
    if not isinstance(event, dict):
        return {}

    if isinstance(event.get("cts"), dict):
        return event["cts"]

    records = event.get("record")
    if isinstance(records, list) and records and isinstance(records[0], dict):
        inner = records[0].get("smn", {}).get("message")
        return _decode(inner)

    if "message" in event:
        return _decode(event["message"])

    return event


def _decode(value):
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return value if isinstance(value, dict) else {}


def event_kind(event):
    """Classify an invocation without assuming a single delivery channel."""
    if not isinstance(event, dict):
        return "UNKNOWN"
    raw = event.get("trigger_type") or event.get("source") or ""
    if str(raw).lower() in SCHEDULE_MARKERS:
        return "SCHEDULE"
    if "record" in event or "cts" in event or "message" in event:
        return "NOTIFICATION"
    if event.get("httpMethod") or event.get("requestContext"):
        return "HTTP"
    if "bucket" in event or "key" in event:
        return "MANUAL"
    return "UNKNOWN"


def object_ref(record):
    """Extract bucket and object key from a notification or a manual event."""
    if not isinstance(record, dict):
        return "", ""
    request = record.get("request")
    if not isinstance(request, dict):
        request = {}
    bucket = (
        request.get("bucketName")
        or request.get("bucket")
        or record.get("bucketName")
        or record.get("bucket")
        or record.get("resource_name")
        or ""
    )
    key = (
        request.get("key")
        or request.get("objectName")
        or request.get("object_key")
        or record.get("objectName")
        or record.get("object_key")
        or record.get("key")
        or ""
    )
    return str(bucket), str(key).lstrip("/")


def is_write_event(record):
    name = str(
        record.get("trace_name")
        or record.get("eventName")
        or record.get("operation")
        or ""
    ).lower()
    if not name:
        return True  # manual events carry no operation name
    return any(marker in name for marker in WRITE_MARKERS)
