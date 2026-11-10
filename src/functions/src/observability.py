"""Structured, dependency-free logging helpers."""
import json
import logging


def make_logger(config):
    logger = logging.getLogger(config.service_name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, str(config.log_level).upper(), logging.INFO))
    return logger


def emit(log_sink, level, event, **fields):
    line = json.dumps({"level": level, "event": event, **fields},
                      ensure_ascii=False, sort_keys=True, default=str)
    if log_sink is None:
        return line
    if hasattr(log_sink, "info"):
        getattr(log_sink, level.lower(), log_sink.info)(line)
    elif callable(log_sink):
        log_sink(line)
    return line
