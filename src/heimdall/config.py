"""Configuration for Heimdall Network Watcher."""
import json
import os
import threading
from pathlib import Path

_LOCK = threading.RLock()

APP_BASE_DIR = Path(__file__).resolve().parents[2]


def _resolve_app_path(env_name, default_name):
    raw = Path(os.environ.get(env_name, default_name)).expanduser()
    if not raw.is_absolute():
        raw = APP_BASE_DIR / raw
    return raw.resolve()


SETTINGS_PATH = _resolve_app_path("HEIMDALL_SETTINGS_FILE", "heimdall.settings.json")

# Base config from environment variables.
_BASE_PING_TARGETS_RAW = os.environ.get("HEIMDALL_PING_TARGETS", "8.8.8.8,1.1.1.1")
_BASE_PING_TARGET = os.environ.get("HEIMDALL_PING_TARGET")
_BASE_POLL_INTERVAL = int(os.environ.get("HEIMDALL_POLL_INTERVAL", "10"))
_BASE_PING_TIMEOUT = int(os.environ.get("HEIMDALL_PING_TIMEOUT", "5"))

# SQLite database path
DATABASE_PATH = str(_resolve_app_path("HEIMDALL_DB", "heimdall.db"))

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


def _normalize_targets(value):
    if value is None:
        raise ValueError("ping_targets is required.")

    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        raw_items = [str(item).strip() for item in value]
    else:
        raise ValueError("ping_targets must be a comma-separated string or a list.")

    normalized = []
    for item in raw_items:
        if not item:
            continue
        normalized.append(_normalize_target(item))

    # Preserve order while removing duplicates.
    deduped = list(dict.fromkeys(normalized))
    if not deduped:
        raise ValueError("ping_targets must include at least one target.")
    return deduped


def _validate_update(payload):
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object.")
    normalized = {}
    if "ping_targets" in payload:
        normalized["PING_TARGETS"] = _normalize_targets(payload["ping_targets"])
    if "ping_target" in payload:
        normalized["PING_TARGETS"] = [_normalize_target(payload["ping_target"])]
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
    primary_target = PING_TARGETS[0] if PING_TARGETS else None
    return {
        "ping_target": primary_target,
        "ping_targets": list(PING_TARGETS),
        "poll_interval": POLL_INTERVAL,
        "ping_timeout": PING_TIMEOUT,
        "settings_file": str(SETTINGS_PATH),
    }


def get_runtime_config():
    with _LOCK:
        return _serialize_runtime()


def update_runtime_config(payload, persist=True):
    global PING_TARGETS, POLL_INTERVAL, PING_TIMEOUT
    normalized = _validate_update(payload)
    with _LOCK:
        next_targets = normalized.get("PING_TARGETS", PING_TARGETS)
        next_interval = normalized.get("POLL_INTERVAL", POLL_INTERVAL)
        next_timeout = normalized.get("PING_TIMEOUT", PING_TIMEOUT)
        if next_timeout > next_interval:
            raise ValueError("ping_timeout cannot be greater than poll_interval.")
        PING_TARGETS = next_targets
        POLL_INTERVAL = next_interval
        PING_TIMEOUT = next_timeout
        if persist:
            _write_settings_file(
                {
                    "PING_TARGETS": list(PING_TARGETS),
                    "POLL_INTERVAL": POLL_INTERVAL,
                    "PING_TIMEOUT": PING_TIMEOUT,
                }
            )
        return _serialize_runtime()


_stored = _read_settings_file()
if "PING_TARGETS" in _stored:
    _initial_targets = _stored.get("PING_TARGETS")
elif "PING_TARGET" in _stored:
    _initial_targets = [_stored.get("PING_TARGET")]
elif _BASE_PING_TARGET:
    _initial_targets = [_BASE_PING_TARGET]
else:
    _initial_targets = _BASE_PING_TARGETS_RAW

PING_TARGETS = _normalize_targets(_initial_targets)
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
