# Network Health Monitor

These scripts periodically monitor network health and provide some rudimentary reporting.

`monitor.py` should be run as a Windows Task as soon as the machine is started. It writes network stats to a SQLite database.

`generate_report.py` reads from the database and generates a static HTML file showing graphs of the network stats. It's a snapshot of the previous 7 days of data, not a live/auto-refreshing page. You'll need to run it again anytime you want fresh data. You can save the HTML file or print it to PDF if you want to save snapshots.

`Check Network Health.bat` is a batch file that runs `generate_report.py`. You can make a shortcut to it on your desktop.

`config.py` contains all the configuration parameters necessary for a given location, especially frequency and monitoring targets like DNS and local gateway.

Speed tests are performed using the Ookla speedtest CLI executabble, `speedtest.exe`, which comes from https://www.speedtest.net/apps/cli. Drop it into the same directory as the scripts.

The report uses two JavaScript libraries served by CDN: `chart.js` and `chartjs-adapter-date-fns`. If you prefer reporting to be fully offline, then download these scripts to the same directory as the report and update the corresponding `<script>` tags in `report_template.html`.