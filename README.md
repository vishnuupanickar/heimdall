<p align="center">
  <img src="src/static/logo.png" alt="Heimdall logo" width="420" />
</p>

[![Upload Python Package](https://github.com/vishnuupanickar/heimdall/actions/workflows/python-publish.yml/badge.svg?branch=master)](https://github.com/vishnuupanickar/heimdall/actions/workflows/python-publish.yml)
# Heimdall Network Watcher

A Python app that continuously polls your home WiFi and network uptime, logs any downtime, and serves a live status dashboard in your browser. The dashboard can be accessed by any device on the same network.

![Alt text](/src/static/screenshot.png?raw=true "Heimdall App")


## Features

- **Continuous monitoring** - Pings a configurable target (default: `8.8.8.8`) at a set interval
- **Downtime logging** - Records each outage with start and end time in SQLite
- **Live dashboard** - Web UI showing current status, 24h uptime %, and recent downtime events
- **Cross-platform** - Uses the system `ping` command (Windows and Unix)

## Quick start

Project structure:

```text
heimdall/
  pyproject.toml
  README.md
  src/
    app.py
    config.py
    database.py
    heimdall.py
    templates/
      dashboard.html
    static/
      style.css
      logo.png
```

1. **Create a virtual environment and install dependencies**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

2. **Run the app**

   ```bash
   python src/app.py
   ```

3. **Open the dashboard**

   In your browser go to: **http://localhost:9000**
   On the same WiFi, other devices can use **http://<your-computer-lan-ip>:9000** (for example, `http://192.168.1.42:9000`).

The monitor runs in the background and the dashboard auto-refreshes every few seconds.

## Configuration

Environment variables (optional):

| Variable | Description | Default |
|----------|-------------|---------|
| `HEIMDALL_PING_TARGET` | Host to ping (IP or hostname) | `8.8.8.8` |
| `HEIMDALL_POLL_INTERVAL` | Seconds between checks | `10` |
| `HEIMDALL_PING_TIMEOUT` | Ping timeout in seconds | `5` |
| `HEIMDALL_DB` | SQLite database path | `heimdall.db` |
| `HEIMDALL_HOST` | Flask bind address | `0.0.0.0` |
| `HEIMDALL_PORT` | Flask port | `9000` |

**Example:** Monitor your router and check every 5 seconds:

```bash
set HEIMDALL_PING_TARGET=8.8.8.8
set HEIMDALL_POLL_INTERVAL=5
python src/app.py
```

On Linux/macOS use `export HEIMDALL_PING_TARGET=192.168.1.1` etc.

## API

- `GET /` - Dashboard (HTML)
- `GET /api/status` - Current status (up/down, last check, current downtime)
- `GET /api/stats` - 24h uptime % and sample count
- `GET /api/downtimes` - Recent downtime intervals

## Requirements

- Python 3.8+
- Flask (see `requirements.txt`)

No special permissions needed; uses standard `ping` and a local SQLite file.
