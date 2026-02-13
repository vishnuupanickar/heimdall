"""Flask app: API and live status dashboard."""
import time
from flask import Flask, jsonify, render_template

import config
import database
from heimdall import get_status, start_monitor

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("dashboard.html", target=config.PING_TARGET)


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


def main():
    start_monitor()
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, threaded=True)


if __name__ == "__main__":
    main()
