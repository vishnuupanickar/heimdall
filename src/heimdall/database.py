"""SQLite storage for downtime events and status."""
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from . import config


def get_db_path() -> Path:
    return Path(config.DATABASE_PATH).resolve()


@contextmanager
def get_connection():
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS downtime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at REAL NOT NULL,
                ended_at REAL,
                created_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS status_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at REAL NOT NULL,
                up INTEGER NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_downtime_started ON downtime(started_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status_log_at ON status_log(at)")


def record_down():
    """Record the start of a downtime (call when transition from up -> down)."""
    now = time.time()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO downtime (started_at, ended_at, created_at) VALUES (?, NULL, ?)",
            (now, now),
        )


def record_up():
    """Record the end of the current downtime (call when transition from down -> up)."""
    now = time.time()
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT id FROM downtime WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            conn.execute("UPDATE downtime SET ended_at = ? WHERE id = ?", (now, row["id"]))


def log_status(up: bool):
    """Append a status sample for stats (optional, can be thinned to avoid huge table)."""
    now = time.time()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO status_log (at, up) VALUES (?, ?)",
            (now, 1 if up else 0),
        )


def get_recent_downtimes(limit: int = 50):
    """Return recent downtime intervals (with ended_at set)."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, started_at, ended_at, created_at
            FROM downtime
            WHERE ended_at IS NOT NULL
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_current_downtime():
    """Return the current open downtime if any."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT id, started_at, created_at FROM downtime WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_uptime_stats():
    """Compute uptime percentage and total downtime from status_log over last 24h (or all if small)."""
    with get_connection() as conn:
        day_ago = time.time() - 24 * 3600
        cursor = conn.execute(
            "SELECT at, up FROM status_log WHERE at >= ? ORDER BY at ASC",
            (day_ago,),
        )
        rows = cursor.fetchall()
    if not rows:
        return {"uptime_pct": None, "samples": 0, "downtime_seconds": None}
    total = len(rows)
    up_count = sum(1 for r in rows if r["up"])
    # Approximate downtime in seconds (each sample is ~ POLL_INTERVAL)
    interval = config.POLL_INTERVAL
    downtime_seconds = (total - up_count) * interval
    uptime_pct = (up_count / total * 100) if total else None
    return {
        "uptime_pct": round(uptime_pct, 2) if uptime_pct is not None else None,
        "samples": total,
        "downtime_seconds": downtime_seconds,
    }


def get_last_status():
    """Get the most recent status_log entry."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT at, up FROM status_log ORDER BY at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return dict(row) if row else None
