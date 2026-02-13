"""Network connectivity monitor: pings target at interval and logs downtime."""
import platform
import subprocess
import threading
import time

from . import config
from . import database

# Global state for the dashboard
_current_status = {"up": None, "last_check": None, "last_change": None}
_lock = threading.Lock()


def _ping_host(host: str, timeout_seconds: int) -> bool:
    """Return True if host is reachable, False otherwise. Cross-platform."""
    try:
        if platform.system().lower() == "windows":
            cmd = ["ping", "-n", "1", "-w", str(timeout_seconds * 1000), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(timeout_seconds), host]
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout_seconds + 2,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False


def get_status():
    """Return current status dict for API/dashboard."""
    with _lock:
        return dict(_current_status)


def _run_loop():
    was_up = None
    while True:
        up = _ping_host(config.PING_TARGET, config.PING_TIMEOUT)
        now = time.time()
        with _lock:
            _current_status["up"] = up
            _current_status["last_check"] = now
            if was_up is not None and was_up != up:
                _current_status["last_change"] = now
                if up:
                    database.record_up()
                else:
                    database.record_down()
            was_up = up
        database.log_status(up)
        time.sleep(config.POLL_INTERVAL)


def start_monitor():
    """Start the monitor in a background daemon thread."""
    database.init_db()
    thread = threading.Thread(target=_run_loop, daemon=True)
    thread.start()
    return thread
