"""FunctionGraph entry point for the upload content check workflow."""
import json
import time
import uuid

from config import load_config
from events import event_kind, is_write_event, object_ref, unwrap
from inspection import inspect
from observability import emit, make_logger
from storage import list_keys, make_client, read_object, remove_object, write_status

HANDLER_NAME = "index.handler"


def create_handler(deps=None):
    deps = deps or {}

    def handler(event, context=None):
        cfg = deps.get("config") or load_config()
        log_sink = deps.get("log_sink")
        logger = log_sink if log_sink is not None else make_logger(cfg)
        started = time.time()
        kind = event_kind(event)
        trace_id = str(
            (event or {}).get("trace_id")
            or (event or {}).get("x-trace-id")
            or uuid.uuid4()
        ) if isinstance(event, dict) else str(uuid.uuid4())

        record = unwrap(event)
        bucket, key = object_ref(record)
        if not bucket:
            bucket = cfg.bucket
        if cfg.content_prefix and not key.startswith(cfg.content_prefix):
            return _reply(200, {
                "traceId": trace_id, "mode": kind, "status": "skipped",
                "reason": "outside-configured-prefix",
            })

        factory = deps.get("client_factory")
        client = (
            factory(cfg.region, cfg.obs_endpoint)
            if factory else make_client(cfg.region, cfg.obs_endpoint, context=context)
        )

        if kind == "SCHEDULE":
            keys = list_keys(client, bucket, cfg.content_prefix)
            emit(logger, "INFO", "periodic-review", traceId=trace_id,
                 bucket=bucket, objects=len(keys))
            return _reply(200, {
                "traceId": trace_id, "mode": kind, "status": "reviewed",
                "objects": len(keys),
            })

        if not key:
            return _reply(400, {
                "traceId": trace_id, "mode": kind, "status": "invalid",
                "reason": "object-key-missing",
            })

        if not is_write_event(record):
            return _reply(200, {
                "traceId": trace_id, "mode": kind, "status": "skipped",
                "reason": "not-a-write-operation", "bucket": bucket, "key": key,
            })

        writer = deps.get("write_status") or write_status
        remover = deps.get("remove_object") or remove_object
        reader = deps.get("read_object") or read_object
        checker = deps.get("inspect") or inspect

        writer(client, bucket, key, "in-progress")
        content = reader(client, bucket, key)
        verdict = checker(content, rules=deps.get("rules"))

        if verdict["clean"]:
            writer(client, bucket, key, "clean")
            action = "kept"
            status = "clean"
        elif cfg.preferred_action == "delete":
            remover(client, bucket, key)
            action = "deleted"
            status = "matched"
        else:
            writer(client, bucket, key, "quarantined", verdict["findings"])
            action = "tagged"
            status = "matched"

        emit(logger, "INFO", "object-checked", traceId=trace_id, mode=kind,
             bucket=bucket, key=key, status=status, action=action,
             bytes=verdict["bytes"], rules=verdict["rules"],
             elapsedMs=int((time.time() - started) * 1000))

        return _reply(200, {
            "traceId": trace_id,
            "mode": kind,
            "bucket": bucket,
            "key": key,
            "status": status,
            "action": action,
            "bytes": verdict["bytes"],
            "findings": verdict["findings"],
            "rules": verdict["rules"],
        })

    return handler


def _reply(status_code, payload):
    return {
        "statusCode": status_code,
        "body": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        "isBase64Encoded": False,
    }


handler = create_handler()
