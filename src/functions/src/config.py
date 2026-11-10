"""Runtime configuration for the upload content check function."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Config:
    region: str = "cn-north-4"
    bucket: str = ""
    obs_endpoint: str = ""
    preferred_action: str = "delete"
    content_prefix: str = ""
    service_name: str = "upload-content-check"
    log_level: str = "INFO"


def load_config(env=None):
    values = env if env is not None else os.environ
    action = (values.get("PREFERRED_ACTION") or "delete").lower()
    if action not in ("delete", "tag"):
        action = "delete"
    return Config(
        region=values.get("REGION") or "cn-north-4",
        bucket=values.get("OBS_BUCKET") or "",
        obs_endpoint=values.get("OBS_ENDPOINT") or "",
        preferred_action=action,
        content_prefix=values.get("CONTENT_PREFIX") or "",
        service_name=values.get("SERVICE_NAME") or "upload-content-check",
        log_level=values.get("LOG_LEVEL") or "INFO",
    )
