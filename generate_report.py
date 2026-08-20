import sqlite3
import json
import webbrowser
import os
from datetime import datetime, timedelta

import config

def fetch_data():
    cutoff_time = (datetime.now() - timedelta(days=7)).isoformat()
    
    with sqlite3.connect(config.DB_FILE) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT timestamp, target_name, loss_percent, avg_latency_ms, jitter_ms FROM ping_metrics WHERE timestamp >= ? ORDER BY timestamp ASC", (cutoff_time,))
        ping_rows = cursor.fetchall()

        cursor.execute("SELECT timestamp, hostname, lookup_time_ms, success FROM dns_metrics WHERE timestamp >= ? ORDER BY timestamp ASC", (cutoff_time,))
        dns_rows = cursor.fetchall()

        cursor.execute("SELECT timestamp, download_mbps, upload_mbps, ping_latency_ms, server_name FROM speed_metrics WHERE timestamp >= ? ORDER BY timestamp ASC", (cutoff_time,))
        speed_rows = cursor.fetchall()

    return ping_rows, dns_rows, speed_rows


def generate_html(ping_data, dns_data, speed_data):
    formatted_ping = [{"x": ts, "target": name, "loss": loss, "latency": lat or 0, "jitter": jitter or 0} for ts, name, loss, lat, jitter in ping_data]
    formatted_dns = [{"x": ts, "lookup_ms": ms or 0, "success": succ} for ts, host, ms, succ in dns_data]
    formatted_speed = [{"x": ts, "download": dl or 0, "upload": ul or 0, "latency": lat or 0, "server": srv} for ts, dl, ul, lat, srv in speed_data]

    timestamp_str = datetime.now().strftime("%A %Y-%m-%d %H:%M:%S")

    with open(config.TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template_content = f.read()

    # Populate placeholders
    html_content = template_content.replace("__GENERATED_AT__", timestamp_str)
    html_content = html_content.replace("__PING_DATA__", json.dumps(formatted_ping))
    html_content = html_content.replace("__DNS_DATA__", json.dumps(formatted_dns))
    html_content = html_content.replace("__SPEED_DATA__", json.dumps(formatted_speed))
    html_content = html_content.replace("__GAP_THRESHOLD__", str(config.GAP_THRESHOLD_MS))
    html_content = html_content.replace("__REPORT_TITLE__", config.REPORT_TITLE)

    with open(config.OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)


if __name__ == "__main__":
    p_data, d_data, s_data = fetch_data()
    generate_html(p_data, d_data, s_data)
    webbrowser.open(f"file://{os.path.abspath(config.OUTPUT_HTML)}")