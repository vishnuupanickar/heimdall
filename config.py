"""Configuration for Heimdall Network Watcher."""
import os

# Host to ping (default: Google DNS; use your router IP for "home wifi" only)
PING_TARGET = os.environ.get("HEIMDALL_PING_TARGET", "8.8.8.8")

# How often to check connectivity (seconds)
POLL_INTERVAL = int(os.environ.get("HEIMDALL_POLL_INTERVAL", "10"))

# Ping timeout in seconds
PING_TIMEOUT = int(os.environ.get("HEIMDALL_PING_TIMEOUT", "5"))

# SQLite database path
DATABASE_PATH = os.environ.get("HEIMDALL_DB", "heimdall.db")

# Flask server host and port
SERVER_HOST = os.environ.get("HEIMDALL_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("HEIMDALL_PORT", "5050"))
