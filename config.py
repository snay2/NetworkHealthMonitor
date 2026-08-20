# ==========================
# NETWORK CONFIGURATION
# ==========================
TARGETS = {
    "LAN_Gateway": "192.168.1.1", # TODO Update for office network
    "Cloudflare_DNS": "1.1.1.1",
    "Google_DNS": "8.8.8.8"
}
DNS_TEST_HOST = "google.com"

# MONITORING CONFIGURATION
DB_FILE = "network_monitor.db"
SAMPLE_INTERVAL = 30            # Seconds between ICMP/DNS probe cycles
PING_COUNT = 10                 # Packets per target
SPEEDTEST_INTERVAL_HOURS = 0.25 # Hours between speed tests; set to 0 to disable speed tests
SPEEDTEST_EXE = "speedtest.exe" # Path to Ookla CLI executable
RETENTION_DAYS = 30             # Days to retain historical data in SQLite

# REPORTING CONFIGURATION
OUTPUT_HTML = "network_report.html"
REPORT_TITLE = "Network Health"
TEMPLATE_FILE = "report_template.html"
GAP_THRESHOLD_MS = 180000       # Max gap between data points before breaking the graph line (default 3 minutes)
