# avalonhome-prometheus-exporter

⚠️ IMPORTANT NOTE: I vibe-coded the shit out of this on ChatGPT & Claude.

A lightweight, zero-dependency Prometheus exporter for **Avalon Home-series ASIC miners**, including:

- **Avalon Nano 3S**
- **Avalon Mini 3**
- Other Avalon Home-series miners using the CGMiner TCP API

The exporter polls miners over their CGMiner TCP API (default port **4028**) and exposes a Prometheus-compatible `/metrics` endpoint with accurate, low-level miner telemetry suitable for Grafana dashboards and long-term monitoring.

---

## 🚀 Features

✔ Supports **multiple miners** (comma-separated hostnames/IPs)  
✔ Automatic detection of **Nano 3S** and **Mini 3** via `version`  
✔ Uses CGMiner API commands combined into a single request:
- `version`
- `summary`
- `stats`
- `config`
- `devs`
- `devdetails`
- `pools`

✔ Collects:
- Hashrate (GHS)
- Temperatures (inlet, outlet, average, max, target)
- Fan RPM and duty %
- Share stats (accepted, rejected, stale)
- Pool performance (per pool index)
- Work utility
- Hardware error counters and rates
- Firmware / model / hardware identifiers
- Up/down state tracking & down-duration timers
- Scrape error counters and state transitions

✔ Optional extended telemetry:
- Per-chip voltage telemetry (PVT_V0)
- Per-chip matching-work telemetry (MW0)
- Power / board telemetry (MPO / PS)
- Extended pool/network counters from `stats`

✔ Dynamic Prometheus labels (model, firmware, pool_index, URL, etc.)  
✔ Pure Python single-file exporter (standard library only)  
✔ Single Docker image (Python 3.12 Alpine)  
✔ Configuration validation with clear error messages  
✔ Improved error handling with specific exception types  
✔ Structured logging with configurable log levels  
✔ Parallel scraping for multiple miners (faster performance)  
✔ Error categorization by type (timeout, connection refused, network, parse, other)  
✔ Graceful shutdown handling  
✔ Debug and version endpoints for troubleshooting

---

## 🚀 Quickstart (Docker Compose)

1. Clone the repository:

```bash
git clone https://github.com/brav0charlie/avalonhome-prometheus-exporter.git
cd avalonhome-prometheus-exporter
```

2. Copy and edit the environment file:

```bash
cp .env.example .env
```

Edit `.env`:

```ini
# --- Miner Targets ---
# Set ONE of these and comment out the other
AVALON_IP="192.168.1.50"
#AVALON_IPS="192.168.1.50,192.168.1.51,miner3.example.com"

# --- Miner API Port ---
AVALON_PORT=4028

# --- Exporter Poll Interval (seconds) ---
UPDATE_INTERVAL=15

# --- Exporter Listen Port ---
EXPORTER_PORT=9100

# --- Extended Metrics ---
# Enable extra high-cardinality / per-chip telemetry (PVT_V0, MW0, etc.)
EXPORT_CHIP_METRICS=false

# --- Miner API Timeout (optional) ---
# TCP connection timeout in seconds (default: 5.0)
MINER_TIMEOUT=5.0

# --- Logging Configuration (optional) ---
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
#LOG_LEVEL=INFO
```

3. Start the exporter:

```bash
docker compose up -d
```

4. Verify operation:

```bash
docker compose logs -f avalon-exporter
```

5. Access metrics:

```
http://localhost:9100/metrics
```

6. Check exporter health and version:

```
http://localhost:9100/health
http://localhost:9100/version
http://localhost:9100/debug
```

---

## 🐳 Docker Usage

### Single Miner

```bash
docker run -d \
  --name avalon-exporter \
  --network host \
  -e AVALON_IP="192.168.1.50" \
  -e AVALON_PORT=4028 \
  -e UPDATE_INTERVAL=15 \
  -e EXPORTER_PORT=9100 \
  -e EXPORT_CHIP_METRICS=false \
  -e MINER_TIMEOUT=5.0 \
  -e LOG_LEVEL=INFO \
  avalonhome-prometheus-exporter
```

### Multiple Miners

```bash
docker run -d \
  --name avalon-exporter \
  --network host \
  -e AVALON_IPS="nano3s-01.local,mini3-rack1.lan,192.168.1.99" \
  -e AVALON_PORT=4028 \
  -e UPDATE_INTERVAL=15 \
  -e EXPORTER_PORT=9100 \
  -e EXPORT_CHIP_METRICS=false \
  -e MINER_TIMEOUT=5.0 \
  -e LOG_LEVEL=INFO \
  avalonhome-prometheus-exporter
```

---

## 🛠 Environment Variables

- `AVALON_IP` — Single miner hostname/IP
- `AVALON_IPS` — Comma-separated miners
- `AVALON_PORT` — Miner TCP API port (default: `4028`)
- `UPDATE_INTERVAL` — Polling frequency in seconds (default: `10`, must be > 0)
- `EXPORTER_PORT` — Exporter HTTP port (default: `9100`, must be 1-65535)
- `EXPORT_CHIP_METRICS` — Enable per-chip telemetry (PVT_V0, MW0, and other high-cardinality metrics)
- `MINER_TIMEOUT` — TCP connection timeout to miner API in seconds (default: `5.0`, must be > 0)
- `LOG_LEVEL` — Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: `INFO`)

Only one of `AVALON_IP` or `AVALON_IPS` must be set.

**Configuration Validation:** The exporter validates all configuration values at startup and will exit with clear error messages if any values are invalid (e.g., negative intervals, out-of-range ports, invalid hostnames).

---

## 📡 Exported Metrics

For detailed information, see `FIELDS-README.md`.

All metrics include the label:

```
ip="192.168.x.x"
```

---

### 🟢 Availability & Status

```
avalon_up
avalon_last_scrape_timestamp_seconds
avalon_down_duration_seconds
avalon_scrape_duration_seconds
avalon_scrape_errors_total
avalon_scrape_errors_timeout_total
avalon_scrape_errors_connection_refused_total
avalon_scrape_errors_network_total
avalon_scrape_errors_parse_total
avalon_scrape_errors_other_total
avalon_status_changes_total
avalon_status_ups_total
avalon_status_downs_total
```

### 📊 Exporter Metrics

```
avalon_exporter_info{version="0.2.0"} 1
```

The exporter also exposes its own version information and scrape duration metrics for monitoring exporter performance.

---

### 🔧 Static Miner Info (Model, Firmware, IDs)

```
avalon_info{
  ip="...",
  model="Nano3s",
  firmware="25061101_97e23a6",
  hwtype="N_MM1v1_X1",
  mac="e0e1a93cecb4",
  dna="02010000c0be9271"
} 1
```

---

### ⚙️ Hashrate Metrics

```
avalon_hashrate_ghs
avalon_hashrate_moving_ghs
avalon_hashrate_avg_ghs
avalon_work_utility
```

Convert to TH/s:

```
avalon_hashrate_ghs / 1000
```

---

### 🌡 Temperature Metrics

```
avalon_temp_inlet_celsius
avalon_temp_outlet_celsius
avalon_temp_avg_celsius
avalon_temp_max_celsius
avalon_temp_target_celsius
avalon_temp_ambient_celsius
```

> Note: `avalon_temp_ambient_celsius` may report a placeholder value on some models (e.g. Nano 3S), but is exported as-is for compatibility with other Avalon Home-series miners.

---

### 🌀 Fan Metrics

```
avalon_fan1_rpm
avalon_fan_duty_percent
```

---

### 🧮 Share & Block Stats

```
avalon_shares_accepted_total
avalon_shares_rejected_total
avalon_shares_stale_total
avalon_blocks_found_total
avalon_best_share
```

---

## 🌐 Pool Metrics (per pool index)

Each pool has labels:

```
ip="..."
pool_index="0"
url="stratum+tcp://pool:3333"
priority="0"
status="Alive"
```

Metrics:

```
avalon_pool_up
avalon_pool_rejected_percent
avalon_pool_stale_percent
avalon_pool_shares_accepted_total
avalon_pool_shares_rejected_total
avalon_pool_shares_stale_total
avalon_pool_current_block_height
```

Additional pool transport counters:

```
avalon_pool_bytes_sent_total
avalon_pool_bytes_recv_total
avalon_pool_times_sent_total
avalon_pool_times_recv_total
```

---

## 🔬 Chip-Level Telemetry (Optional)

These metrics are exported **only** when:

```
EXPORT_CHIP_METRICS=true
```

### Per-chip voltage (PVT_V0)

```
avalon_chip_voltage_volts
```

Values are reported in volts (e.g. `3.03`).

### Per-chip nonce / matching-work telemetry (MW0)

```
avalon_chip_matching_work
```

This represents **per-chip NONCE / matching-work activity**, not power.

Grafana panels consuming these metrics should be configured to **hide when no data is present**.

---

## 🌐 HTTP Endpoints

The exporter provides several HTTP endpoints:

- `/metrics` — Prometheus metrics (main endpoint)
- `/health` — Health check endpoint (returns `OK` and version if healthy)
- `/version` — JSON response with exporter version information
- `/debug` — JSON response with internal state for troubleshooting

**Example:**
```bash
# Health check
curl http://localhost:9100/health
# OK
# version=0.2.0

# Version info
curl http://localhost:9100/version
# {
#   "version": "0.2.0",
#   "exporter": "avalonhome-prometheus-exporter"
# }

# Debug information
curl http://localhost:9100/debug | jq
```

---

## Prometheus Configuration Example

```yaml
scrape_configs:
  - job_name: "avalon"
    scrape_interval: 30s
    static_configs:
      - targets:
          - "exporter-host-1:9100"
          - "exporter-host-2:9100"
```

---

## 📊 Grafana Dashboard

A prebuilt Grafana dashboard is included in the repository and supports:
- Miner selection
- Pool selection
- Optional chip-level panels (hidden automatically if chip metrics are disabled)

---

## 📚 Documentation

Additional documentation is available:

- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Production deployment guide with Docker, systemd, performance tuning, and monitoring recommendations
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — Troubleshooting guide for common issues, error types, and debugging techniques
- **[FIELDS-README.md](FIELDS-README.md)** — Detailed reference for raw miner API fields and how they map to Prometheus metrics

---

## 📁 Project Structure

```
avalonhome-prometheus-exporter/
├── app/
│   └── exporter.py
├── grafana/
│   └── avalonhome-miner-dashboard.json
├── .env.example
├── CHANGELOG.md
├── DEPLOYMENT.md
├── docker-compose.yml
├── Dockerfile
├── FIELDS-README.md
├── LICENSE
├── README.md
└── TROUBLESHOOTING.md
```

---

## ❤️ Contributing

PRs welcome — especially for:

- Additional Avalon miner model support
- New metrics
- Dashboard improvements
- Documentation enhancements

---

## 📜 License

MIT License

---

### ❤️ Acknowledgements

Yes, this project was vibe-coded.  
Yes, it works.  
No, we’re not sorry.  
