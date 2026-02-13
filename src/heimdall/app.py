"""Flask app: API and live status dashboard."""
import socket
import time
from flask import Flask, jsonify, render_template, request

from . import config
from . import database
from .monitor import get_status, start_monitor

app = Flask(__name__, template_folder="templates", static_folder="static")


def _get_local_lan_ip():
    """Best-effort LAN IP detection for sharing URL on local WiFi."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


@app.route("/")
def index():
    return render_template(
        "dashboard.html",
        target=config.PING_TARGET,
        lan_ip=_get_local_lan_ip(),
        flask_port=config.SERVER_PORT,
    )


@app.route("/api/status")
def api_status():
    status = get_status()
    current_downtime = database.get_current_downtime()
    last = database.get_last_status()
    return jsonify({
        "up": status["up"],
        "last_check": status["last_check"],
        "last_change": status["last_change"],
        "current_downtime": current_downtime,
        "last_sample": last,
    })


@app.route("/api/stats")
def api_stats():
    stats = database.get_uptime_stats()
    return jsonify(stats)


@app.route("/api/downtimes")
def api_downtimes():
    limit = 50
    downtimes = database.get_recent_downtimes(limit=limit)
    return jsonify({"downtimes": downtimes})


@app.route("/api/config", methods=["GET"])
def api_get_config():
    return jsonify(config.get_runtime_config())


@app.route("/api/config", methods=["POST"])
def api_update_config():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Expected JSON body."}), 400
    try:
        updated = config.update_runtime_config(payload, persist=True)
        return jsonify(updated)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


def main():
    start_monitor()
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, threaded=True)


if __name__ == "__main__":
    main()
