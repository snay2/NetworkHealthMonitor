import sqlite3
import random
from datetime import datetime, timedelta

DB_FILE = "network_monitor.db"
DAYS_TO_GENERATE = 60
INTERVAL_SECONDS = 15
SPEEDTEST_INTERVAL_SECONDS = 10800  # 3 hours

TARGETS = [
    ("LAN_Gateway", "192.168.178.1", 1.0, 5.0),      # (name, ip, min_lat, max_lat)
    ("Cloudflare_DNS", "1.1.1.1", 10.0, 25.0),
    ("Google_DNS", "8.8.8.8", 15.0, 35.0)
]

def init_db(conn):
    """Creates schema and indexes matching monitor.py."""
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
    
    # Indexes for fast querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ping_ts ON ping_metrics(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dns_ts ON dns_metrics(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_speed_ts ON speed_metrics(timestamp);")
    conn.commit()

def generate_data():
    print(f"Generating {DAYS_TO_GENERATE} days of mock data (15-second intervals)...")
    
    start_time = datetime.now() - timedelta(days=DAYS_TO_GENERATE)
    end_time = datetime.now()
    current_time = start_time

    ping_records = []
    dns_records = []
    speed_records = []

    last_speedtest_time = start_time - timedelta(seconds=SPEEDTEST_INTERVAL_SECONDS)

    while current_time <= end_time:
        ts_str = current_time.isoformat()

        # 1. Ping Metrics
        for name, ip, min_lat, max_lat in TARGETS:
            # Simulate occasional transient packet loss (1% chance)
            loss = 10.0 if random.random() < 0.01 else 0.0
            lat = round(random.uniform(min_lat, max_lat), 2)
            jitter = round(random.uniform(0.1, 4.0), 2)
            ping_records.append((ts_str, name, ip, loss, lat, jitter))

        # 2. DNS Metrics
        dns_lat = round(random.uniform(5.0, 30.0), 2)
        dns_records.append((ts_str, "google.com", dns_lat, 1))

        # 3. Speed Test Metrics (Every 3 hours)
        if (current_time - last_speedtest_time).total_seconds() >= SPEEDTEST_INTERVAL_SECONDS:
            dl = round(random.uniform(250.0, 500.0), 2)
            ul = round(random.uniform(20.0, 50.0), 2)
            speed_lat = round(random.uniform(8.0, 15.0), 2)
            speed_records.append((ts_str, dl, ul, speed_lat, "Comcast (Dallas, TX)"))
            last_speedtest_time = current_time

        current_time += timedelta(seconds=INTERVAL_SECONDS)

    print(f"Generated {len(ping_records):,} ping records, {len(dns_records):,} DNS records, and {len(speed_records):,} speed test records.")
    
    # Bulk insert into SQLite inside a single fast transaction
    with sqlite3.connect(DB_FILE) as conn:
        init_db(conn)
        cursor = conn.cursor()
        
        print("Inserting into SQLite database...")
        cursor.executemany("""
            INSERT INTO ping_metrics (timestamp, target_name, target_ip, loss_percent, avg_latency_ms, jitter_ms)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ping_records)

        cursor.executemany("""
            INSERT INTO dns_metrics (timestamp, hostname, lookup_time_ms, success)
            VALUES (?, ?, ?, ?)
        """, dns_records)

        cursor.executemany("""
            INSERT INTO speed_metrics (timestamp, download_mbps, upload_mbps, ping_latency_ms, server_name)
            VALUES (?, ?, ?, ?, ?)
        """, speed_records)

        conn.commit()

    print(f"Success! Database '{DB_FILE}' populated.")

if __name__ == "__main__":
    generate_data()