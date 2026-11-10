"""Offline end-to-end checks for the upload content check workflow.

No cloud connection and no external process are used: storage access,
inspection rules, configuration and logging are injected into the handler.
"""
import json
import sys
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src" / "functions" / "src"))

from config import Config, load_config                     # noqa: E402
from events import event_kind, is_write_event, object_ref, unwrap   # noqa: E402
from index import HANDLER_NAME, create_handler            # noqa: E402
from inspection import STANDARD_TEST_SIGNATURE, inspect   # noqa: E402
from observability import emit                            # noqa: E402
from storage import list_keys, read_object, write_status  # noqa: E402


class FakeBody:
    def __init__(self, buffer=b"", contents=None):
        self.buffer = buffer
        self.contents = contents or []


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status = status
        self.body = body or FakeBody()


class FakeItem:
    def __init__(self, key):
        self.key = key


class FakeClient:
    def __init__(self, content=b"hello"):
        self.content = content
        self.deleted = []
        self.metadata = []
        self.objects = [FakeItem("a.txt"), FakeItem("b.txt")]

    def getObject(self, bucket, key, loadStreamInMemory=False):
        assert loadStreamInMemory is True
        return FakeResponse(200, FakeBody(self.content))

    def setObjectMetadata(self, bucket, key, metadata):
        self.metadata.append((bucket, key, dict(metadata)))
        return FakeResponse(200)

    def deleteObject(self, bucket, key):
        self.deleted.append((bucket, key))
        return FakeResponse(204)

    def listObjects(self, bucket, prefix=""):
        return FakeResponse(200, FakeBody(contents=self.objects))


def build_deps(client, config=None, rules=None):
    lines = []
    return {
        "config": config or Config(bucket="demo-bucket"),
        "client_factory": lambda region, endpoint: client,
        "log_sink": lines.append,
        "rules": rules,
    }, lines


def call(deps, event):
    return create_handler(deps)(event, context=None)


def body_of(reply):
    return json.loads(reply["body"])


class ConfigTests(unittest.TestCase):
    def test_defaults(self):
        cfg = Config()
        self.assertEqual(cfg.preferred_action, "delete")
        self.assertEqual(cfg.region, "cn-north-4")

    def test_load_from_mapping(self):
        cfg = load_config({"PREFERRED_ACTION": "tag", "OBS_BUCKET": "b"})
        self.assertEqual(cfg.preferred_action, "tag")
        self.assertEqual(cfg.bucket, "b")

    def test_invalid_action_falls_back(self):
        self.assertEqual(load_config({"PREFERRED_ACTION": "move"}).preferred_action,
                         "delete")


class EventTests(unittest.TestCase):
    def test_smn_envelope_is_unwrapped(self):
        inner = {"trace_name": "createObject",
                 "request": {"bucketName": "b", "key": "k.txt"}}
        event = {"record": [{"smn": {"message": json.dumps(inner)}}]}
        self.assertEqual(unwrap(event)["trace_name"], "createObject")

    def test_direct_record_is_unwrapped(self):
        cts = {"trace_name": "createObject"}
        self.assertEqual(unwrap({"cts": cts}), cts)

    def test_plain_message_is_unwrapped(self):
        self.assertEqual(unwrap({"message": '{"a":1}'}), {"a": 1})

    def test_bad_json_yields_empty_record(self):
        self.assertEqual(unwrap({"message": "not-json"}), {})

    def test_manual_event_passes_through(self):
        event = {"bucket": "b", "key": "k"}
        self.assertEqual(unwrap(event), event)

    def test_event_kinds(self):
        self.assertEqual(event_kind({"trigger_type": "TIMER"}), "SCHEDULE")
        self.assertEqual(event_kind({"record": []}), "NOTIFICATION")
        self.assertEqual(event_kind({"bucket": "b", "key": "k"}), "MANUAL")
        self.assertEqual(event_kind({"httpMethod": "POST"}), "HTTP")

    def test_object_ref_from_request(self):
        rec = {"request": {"bucketName": "b", "key": "dir/k.txt"}}
        self.assertEqual(object_ref(rec), ("b", "dir/k.txt"))

    def test_object_ref_from_resource_name(self):
        self.assertEqual(object_ref({"resource_name": "b", "key": "k"}), ("b", "k"))

    def test_write_filter(self):
        self.assertTrue(is_write_event({"trace_name": "createObject"}))
        self.assertFalse(is_write_event({"trace_name": "deleteObject"}))
        self.assertTrue(is_write_event({}))


class InspectionTests(unittest.TestCase):
    def test_clean_payload(self):
        result = inspect(b"ordinary content", rules={})
        self.assertTrue(result["clean"])
        self.assertEqual(result["bytes"], 16)

    def test_builtin_rule_matches_test_signature(self):
        result = inspect(b"prefix" + STANDARD_TEST_SIGNATURE + b"suffix")
        self.assertFalse(result["clean"])
        self.assertEqual(result["findings"][0]["rule"], "demo-signature")

    def test_builtin_rule_ignores_clean_payload(self):
        self.assertTrue(inspect(b"hello world")["clean"])

    def test_custom_rule_is_pluggable(self):
        result = inspect(b"abc", rules={"length": lambda b: "too-short" if len(b) < 5 else None})
        self.assertEqual(result["rules"], ["length"])
        self.assertFalse(result["clean"])


class StorageTests(unittest.TestCase):
    def test_read_returns_bytes(self):
        self.assertEqual(read_object(FakeClient(b"xyz"), "b", "k"), b"xyz")

    def test_write_status_records_metadata(self):
        client = FakeClient()
        write_status(client, "b", "k", "clean")
        self.assertEqual(client.metadata[0][2]["check-status"], "clean")

    def test_write_status_includes_findings(self):
        client = FakeClient()
        write_status(client, "b", "k", "quarantined", [{"rule": "r1"}])
        self.assertEqual(client.metadata[0][2]["check-findings"], "r1")

    def test_list_keys(self):
        self.assertEqual(list_keys(FakeClient(), "b"), ["a.txt", "b.txt"])


class HandlerTests(unittest.TestCase):
    def test_clean_object_is_kept_and_marked(self):
        client = FakeClient(b"hello")
        deps, _ = build_deps(client, rules={})
        out = body_of(call(deps, {"bucket": "demo-bucket", "key": "a.txt"}))
        self.assertEqual(out["status"], "clean")
        self.assertEqual(out["action"], "kept")
        self.assertEqual(client.deleted, [])

    def test_matched_object_is_deleted(self):
        client = FakeClient(b"bad " + STANDARD_TEST_SIGNATURE)
        deps, _ = build_deps(client)
        out = body_of(call(deps, {"bucket": "demo-bucket", "key": "bad.txt"}))
        self.assertEqual(out["action"], "deleted")
        self.assertEqual(client.deleted, [("demo-bucket", "bad.txt")])

    def test_matched_object_is_tagged_when_configured(self):
        client = FakeClient(STANDARD_TEST_SIGNATURE)
        deps, _ = build_deps(client, config=Config(bucket="demo-bucket",
                                                   preferred_action="tag"))
        out = body_of(call(deps, {"bucket": "demo-bucket", "key": "bad.txt"}))
        self.assertEqual(out["action"], "tagged")
        self.assertEqual(client.deleted, [])
        self.assertEqual(client.metadata[-1][2]["check-status"], "quarantined")

    def test_in_progress_status_is_written_first(self):
        client = FakeClient(b"hello")
        deps, _ = build_deps(client, rules={})
        call(deps, {"bucket": "demo-bucket", "key": "a.txt"})
        self.assertEqual(client.metadata[0][2]["check-status"], "in-progress")

    def test_smn_envelope_end_to_end(self):
        client = FakeClient(b"hello")
        deps, _ = build_deps(client, rules={})
        inner = {"trace_name": "createObject",
                 "request": {"bucketName": "demo-bucket", "key": "a.txt"}}
        event = {"record": [{"smn": {"message": json.dumps(inner)}}]}
        out = body_of(call(deps, event))
        self.assertEqual(out["status"], "clean")
        self.assertEqual(out["mode"], "NOTIFICATION")

    def test_non_write_operation_is_skipped(self):
        client = FakeClient()
        deps, _ = build_deps(client, rules={})
        event = {"trace_name": "deleteObject", "bucket": "demo-bucket", "key": "a.txt"}
        out = body_of(call(deps, event))
        self.assertEqual(out["status"], "skipped")
        self.assertEqual(client.metadata, [])

    def test_prefix_filter_skips_other_objects(self):
        client = FakeClient()
        deps, _ = build_deps(client, config=Config(bucket="demo-bucket",
                                                   content_prefix="incoming/"),
                             rules={})
        out = body_of(call(deps, {"bucket": "demo-bucket", "key": "other/a.txt"}))
        self.assertEqual(out["status"], "skipped")

    def test_missing_key_returns_400(self):
        client = FakeClient()
        deps, _ = build_deps(client, rules={})
        reply = call(deps, {"bucket": "demo-bucket"})
        self.assertEqual(reply["statusCode"], 400)

    def test_schedule_runs_review_without_rewriting_objects(self):
        client = FakeClient()
        deps, _ = build_deps(client, rules={})
        out = body_of(call(deps, {"trigger_type": "TIMER"}))
        self.assertEqual(out["status"], "reviewed")
        self.assertEqual(out["objects"], 2)
        self.assertEqual(client.metadata, [])
        self.assertEqual(client.deleted, [])

    def test_structured_log_is_emitted(self):
        client = FakeClient(b"hello")
        deps, lines = build_deps(client, rules={})
        call(deps, {"bucket": "demo-bucket", "key": "a.txt"})
        self.assertTrue(any("object-checked" in line for line in lines))

    def test_reply_envelope(self):
        client = FakeClient(b"hello")
        deps, _ = build_deps(client, rules={})
        reply = call(deps, {"bucket": "demo-bucket", "key": "a.txt"})
        self.assertEqual(reply["statusCode"], 200)
        self.assertFalse(reply["isBase64Encoded"])

    def test_emit_returns_json_line(self):
        line = emit(None, "INFO", "unit", value=1)
        self.assertEqual(json.loads(line)["value"], 1)

    def test_handler_name_constant(self):
        self.assertEqual(HANDLER_NAME, "index.handler")


class ArchiveTests(unittest.TestCase):
    def test_archive_contains_only_project_modules(self):
        zip_path = REPO / "build" / "function.zip"
        self.assertTrue(zip_path.exists(), "run scripts/package-function.sh first")
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
        expected = {"config.py", "events.py", "index.py", "inspection.py",
                    "observability.py", "storage.py"}
        self.assertTrue(expected.issubset(set(names)))
        self.assertTrue(all(name.endswith(".py") for name in names))
        bundled_clients = [n for n in names
                           if n.startswith("obs/") or n in ("obs.py", "requests.py")]
        self.assertEqual(bundled_clients, [])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print("=== Summary: %d passed, %d failed ===" % (
        result.testsRun - len(result.failures) - len(result.errors),
        len(result.failures) + len(result.errors)))
    sys.exit(0 if result.wasSuccessful() else 1)
