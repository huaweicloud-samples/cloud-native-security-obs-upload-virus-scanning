"""Object storage access using the client supplied by the runtime."""
import os


def make_client(region, endpoint=None, context=None):
    from obs import ObsClient

    getters = (
        ("access_key", "getSecurityAccessKey"),
        ("secret_key", "getSecuritySecretKey"),
        ("security_token", "getSecurityToken"),
    )
    values = {}
    for key, method in getters:
        getter = getattr(context, method, None) if context is not None else None
        values[key] = getter() if callable(getter) else os.environ.get(key.upper(), "")

    server = endpoint or "https://obs.%s.myhuaweicloud.com" % region
    return ObsClient(
        access_key_id=values["access_key"],
        secret_access_key=values["secret_key"],
        security_token=values["security_token"],
        server=server,
    )


def _status(response):
    return int(getattr(response, "status", 0) or 0)


def read_object(client, bucket, key):
    response = client.getObject(bucket, key, loadStreamInMemory=True)
    if _status(response) >= 300:
        raise RuntimeError("read failed with status %d" % _status(response))
    body = getattr(response, "body", None)
    buffer = getattr(body, "buffer", None)
    if buffer is None:
        raise RuntimeError("read returned no content")
    return buffer if isinstance(buffer, bytes) else bytes(buffer)


def write_status(client, bucket, key, status, findings=None):
    metadata = {
        "check-status": status,
        "check-findings": ",".join(
            f.get("rule", "") for f in (findings or [])
        ),
    }
    for method_name in ("setObjectMetadata", "putObjectMetadata"):
        method = getattr(client, method_name, None)
        if not callable(method):
            continue
        try:
            response = method(bucket, key, metadata)
        except TypeError:
            response = method(bucket, key, metadata=metadata)
        return _status(response)
    raise RuntimeError("no metadata writer available on the client")


def remove_object(client, bucket, key):
    response = client.deleteObject(bucket, key)
    if _status(response) >= 300:
        raise RuntimeError("delete failed with status %d" % _status(response))
    return _status(response)


def list_keys(client, bucket, prefix=""):
    response = client.listObjects(bucket, prefix=prefix)
    if _status(response) >= 300:
        raise RuntimeError("list failed with status %d" % _status(response))
    body = getattr(response, "body", None)
    contents = getattr(body, "contents", None) or []
    return [str(getattr(item, "key", "")) for item in contents]
