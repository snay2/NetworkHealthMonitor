import sqlite3
import subprocess
import re
import time
import socket
import json
import os
from datetime import datetime, timedelta
from statistics import mean

import config

# ==========================
# DATABASE SETUP
# ==========================
def init_db():
    """Initializes SQLite tables for ping, DNS, and speed test metrics."""
    with sqlite3.connect(config.DB_FILE) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ping_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                target_name TEXT NOT NULL,
                target_ip TEXT NOT NULL,
                loss_percent REAL NOT NULL,
                avg_latency_ms REAL,
                jitter_ms REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dns_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                hostname TEXT NOT NULL,
                lookup_time_ms REAL,
                success INTEGER NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS speed_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                download_mbps REAL,
                upload_mbps REAL,
                ping_latency_ms REAL,
                server_name TEXT
            )
        """)

        # CREATE INDEXES for fast range queries and deletion
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ping_ts ON ping_metrics(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dns_ts ON dns_metrics(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_speed_ts ON speed_metrics(timestamp);")

        conn.commit()

def prune_old_data():
    """Deletes records older than RETENTION_DAYS to control disk space."""
    cutoff = (datetime.now() - timedelta(days=config.RETENTION_DAYS)).isoformat()
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ping_metrics WHERE timestamp < ?", (cutoff,))
            cursor.execute("DELETE FROM dns_metrics WHERE timestamp < ?", (cutoff,))
            cursor.execute("DELETE FROM speed_metrics WHERE timestamp < ?", (cutoff,))
            conn.commit()
    except Exception:
        pass
    
# ==========================
# PROBE FUNCTIONS
# ==========================
def run_ping_probe(ip, count=config.PING_COUNT):
    cmd = ["ping", "-n", str(count), "-w", "1000", ip]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=(count * 2))
        output = result.stdout
    except Exception:
        return 100.0, None, None

    latencies = [float(m) for m in re.findall(r"time[=<]\s*([0-9]+)ms", output, re.IGNORECASE)]
    received_count = len(latencies)
    loss_percent = ((count - received_count) / count) * 100.0

    if received_count == 0:
        return loss_percent, None, None

    avg_latency = mean(latencies)
    jitter = mean([abs(latencies[i+1] - latencies[i]) for i in range(len(latencies) - 1)]) if received_count >= 2 else 0.0

    return loss_percent, round(avg_latency, 2), round(jitter, 2)


def run_dns_probe(hostname=config.DNS_TEST_HOST):
    start_time = time.perf_counter()
    try:
        socket.gethostbyname(hostname)
        end_time = time.perf_counter()
        return round((end_time - start_time) * 1000.0, 2), 1
    except socket.gaierror:
        return None, 0


def run_speedtest():
    """Executes speedtest.exe CLI, returning Mbps and latency metrics as JSON."""
    if not os.path.exists(config.SPEEDTEST_EXE):
        return None

    cmd = [config.SPEEDTEST_EXE, "--format=json", "--accept-license", "--accept-gdpr"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            # Ookla reports bandwidth in bytes/sec; convert to Mbps (bytes * 8 / 1,000,000)
            dl_mbps = round((data["download"]["bandwidth"] * 8) / 1_000_000, 2)
            ul_mbps = round((data["upload"]["bandwidth"] * 8) / 1_000_000, 2)
            ping_ms = round(data["ping"]["latency"], 2)
            server = f"{data['server']['name']} ({data['server']['location']})"
            return dl_mbps, ul_mbps, ping_ms, server
    except Exception:
        pass
    return None

def get_last_speedtest_time():
    """Retrieves the Unix timestamp of the most recent speed test from SQLite."""
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp FROM speed_metrics ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            if row and row[0]:
                # Convert ISO timestamp string back to epoch seconds
                return datetime.fromisoformat(row[0]).timestamp()
    except Exception:
        pass
    return 0  # Fallback if table is empty or DB doesn't exist

# ==========================
# MAIN EXECUTION LOOP
# ==========================
def main():
    init_db()
    prune_old_data()
    last_speedtest_time = get_last_speedtest_time()

    while True:
        current_time_sec = time.time()
        timestamp = datetime.now().isoformat()

        # 1. Check if it's time for a Speed Test (runs every SPEEDTEST_INTERVAL hours)
        if config.SPEEDTEST_INTERVAL_HOURS > 0 and (current_time_sec - last_speedtest_time) >= (config.SPEEDTEST_INTERVAL_HOURS * 60 * 60):
            speed_results = run_speedtest()
            if speed_results:
                dl, ul, ping_lat, server = speed_results
                with sqlite3.connect(config.DB_FILE) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO speed_metrics 
                        (timestamp, download_mbps, upload_mbps, ping_latency_ms, server_name)
                        VALUES (?, ?, ?, ?, ?)
                    """, (timestamp, dl, ul, ping_lat, server))
                    conn.commit()
            last_speedtest_time = time.time()

        # 2. Run Continuous Ping & DNS Probes
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()

            for name, ip in config.TARGETS.items():
                loss, avg_lat, jitter = run_ping_probe(ip)
                cursor.execute("""
                    INSERT INTO ping_metrics 
                    (timestamp, target_name, target_ip, loss_percent, avg_latency_ms, jitter_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (timestamp, name, ip, loss, avg_lat, jitter))

            dns_ms, dns_success = run_dns_probe()
            cursor.execute("""
                INSERT INTO dns_metrics (timestamp, hostname, lookup_time_ms, success)
                VALUES (?, ?, ?, ?)
            """, (timestamp, config.DNS_TEST_HOST, dns_ms, dns_success))

            conn.commit()

        time.sleep(config.SAMPLE_INTERVAL)

if __name__ == "__main__":
    main()