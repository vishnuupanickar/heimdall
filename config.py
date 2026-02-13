"""Configuration for Heimdall Network Watcher."""
import json
import os
import threading
from pathlib import Path

_LOCK = threading.RLock()

SETTINGS_PATH = Path(os.environ.get("HEIMDALL_SETTINGS_FILE", "heimdall.settings.json"))

# Base config from environment variables.
_BASE_PING_TARGET = os.environ.get("HEIMDALL_PING_TARGET", "8.8.8.8")
_BASE_POLL_INTERVAL = int(os.environ.get("HEIMDALL_POLL_INTERVAL", "10"))
_BASE_PING_TIMEOUT = int(os.environ.get("HEIMDALL_PING_TIMEOUT", "5"))

# SQLite database path
DATABASE_PATH = os.environ.get("HEIMDALL_DB", "heimdall.db")

# Flask server host and port
SERVER_HOST = os.environ.get("HEIMDALL_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("HEIMDALL_PORT", "9000"))


def _read_settings_file():
    if not SETTINGS_PATH.exists():
        return {}
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _write_settings_file(data):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _coerce_positive_int(value, name, minimum=1, maximum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer.")
    if parsed < minimum:
        raise ValueError(f"{name} must be >= {minimum}.")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{name} must be <= {maximum}.")
    return parsed


def _normalize_target(value):
    if value is None:
        raise ValueError("ping_target is required.")
    target = str(value).strip()
    if not target:
        raise ValueError("ping_target cannot be empty.")
    if len(target) > 255:
        raise ValueError("ping_target is too long.")
    return target


def _validate_update(payload):
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object.")
    normalized = {}
    if "ping_target" in payload:
        normalized["PING_TARGET"] = _normalize_target(payload["ping_target"])
    if "poll_interval" in payload:
        normalized["POLL_INTERVAL"] = _coerce_positive_int(
            payload["poll_interval"], "poll_interval", minimum=1, maximum=3600
        )
    if "ping_timeout" in payload:
        normalized["PING_TIMEOUT"] = _coerce_positive_int(
            payload["ping_timeout"], "ping_timeout", minimum=1, maximum=60
        )
    if "POLL_INTERVAL" in normalized and "PING_TIMEOUT" in normalized:
        if normalized["PING_TIMEOUT"] > normalized["POLL_INTERVAL"]:
            raise ValueError("ping_timeout cannot be greater than poll_interval.")
    if not normalized:
        raise ValueError("No supported config fields provided.")
    return normalized


def _serialize_runtime():
    return {
        "ping_target": PING_TARGET,
        "poll_interval": POLL_INTERVAL,
        "ping_timeout": PING_TIMEOUT,
        "settings_file": str(SETTINGS_PATH),
    }


def get_runtime_config():
    with _LOCK:
        return _serialize_runtime()


def update_runtime_config(payload, persist=True):
    global PING_TARGET, POLL_INTERVAL, PING_TIMEOUT
    normalized = _validate_update(payload)
    with _LOCK:
        next_target = normalized.get("PING_TARGET", PING_TARGET)
        next_interval = normalized.get("POLL_INTERVAL", POLL_INTERVAL)
        next_timeout = normalized.get("PING_TIMEOUT", PING_TIMEOUT)
        if next_timeout > next_interval:
            raise ValueError("ping_timeout cannot be greater than poll_interval.")
        PING_TARGET = next_target
        POLL_INTERVAL = next_interval
        PING_TIMEOUT = next_timeout
        if persist:
            _write_settings_file(
                {
                    "PING_TARGET": PING_TARGET,
                    "POLL_INTERVAL": POLL_INTERVAL,
                    "PING_TIMEOUT": PING_TIMEOUT,
                }
            )
        return _serialize_runtime()


_stored = _read_settings_file()
PING_TARGET = _normalize_target(_stored.get("PING_TARGET", _BASE_PING_TARGET))
POLL_INTERVAL = _coerce_positive_int(
    _stored.get("POLL_INTERVAL", _BASE_POLL_INTERVAL),
    "poll_interval",
    minimum=1,
    maximum=3600,
)
PING_TIMEOUT = _coerce_positive_int(
    _stored.get("PING_TIMEOUT", _BASE_PING_TIMEOUT),
    "ping_timeout",
    minimum=1,
    maximum=60,
)
if PING_TIMEOUT > POLL_INTERVAL:
    PING_TIMEOUT = min(PING_TIMEOUT, POLL_INTERVAL)
