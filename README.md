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
✔ All metrics include `# HELP` and `# TYPE` annotations for full Prometheus compatibility  
✔ Pure Python single-file exporter (standard library only)  
✔ Single Docker image (Python 3.12 Alpine)  
✔ Configuration validation with clear error messages  
✔ Real hostname/IP validation (IPv4, IPv6, RFC-compliant hostnames)  
✔ Improved error handling with specific exception types  
✔ Structured logging with configurable log levels  
✔ Parallel scraping via thread pool for multiple miners  
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

# --- Debug Endpoint (optional) ---
# Enable the /debug endpoint (default: false)
# Exposes internal state including miner IPs and error messages
#ENABLE_DEBUG_ENDPOINT=false

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
docker compose logs -f avalonhome-exporter
```

5. Access metrics:

```text
http://localhost:9100/metrics
```

6. Check exporter health and version:

```text
http://localhost:9100/health
http://localhost:9100/version
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

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `AVALON_IP` | Single miner hostname/IP | — |
| `AVALON_IPS` | Comma-separated miners | — |
| `AVALON_PORT` | Miner TCP API port | `4028` |
| `UPDATE_INTERVAL` | Polling frequency in seconds (must be > 0) | `10` |
| `EXPORTER_PORT` | Exporter HTTP port (must be 1–65535) | `9100` |
| `EXPORT_CHIP_METRICS` | Enable per-chip telemetry (PVT_V0, MW0, high-cardinality) | `false` |
| `MINER_TIMEOUT` | TCP connection timeout in seconds (must be > 0) | `5.0` |
| `ENABLE_DEBUG_ENDPOINT` | Enable the `/debug` endpoint (exposes internal state including miner IPs and error messages) | `false` |
| `LOG_LEVEL` | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL | `INFO` |

Only one of `AVALON_IP` or `AVALON_IPS` must be set.

**Configuration Validation:** The exporter validates all configuration values at startup and will exit with clear error messages if any values are invalid (e.g., negative intervals, out-of-range ports, invalid hostnames).

---

## 📡 Exported Metrics

For detailed information, see `FIELDS-README.md`.

All metrics include the label:

```text
ip="192.168.x.x"
```

All metrics include `# HELP` and `# TYPE` annotations for full compatibility with `promtool check metrics`, Grafana metric explorer, Prometheus federation, and recording rules.

---

### 🟢 Availability & Status

```text
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

```text
avalon_exporter_info{version="0.3.0"} 1
```

The exporter also exposes its own version information and scrape duration metrics for monitoring exporter performance.

---

### 🔧 Static Miner Info (Model, Firmware, IDs)

```text
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

```text
avalon_hashrate_ghs
avalon_hashrate_moving_ghs
avalon_hashrate_avg_ghs
avalon_work_utility
```

Convert to TH/s:

```text
avalon_hashrate_ghs / 1000
```

---

### 🌡 Temperature Metrics

```text
avalon_temp_inlet_celsius
avalon_temp_outlet_celsius
avalon_temp_avg_celsius
avalon_temp_max_celsius
avalon_temp_target_celsius
```

> Note: `avalon_temp_inlet_celsius` may report `-273` on some Nano 3S firmware. This is exported as-is for cross-model compatibility — treat it as "unavailable" when graphing.

---

### 🌀 Fan Metrics

```text
avalon_fan1_rpm
avalon_fan_duty_percent
```

---

### 🧮 Share & Block Stats

```text
avalon_shares_accepted_total
avalon_shares_rejected_total
avalon_shares_stale_total
avalon_blocks_found_total
avalon_best_share
```

---

## 🌐 Pool Metrics (per pool index)

Each pool has labels:

```text
ip="..."
pool_index="0"
url="stratum+tcp://pool:3333"
priority="0"
status="Alive"
```

Metrics:

```text
avalon_pool_up
avalon_pool_rejected_percent
avalon_pool_stale_percent
avalon_pool_shares_accepted_total
avalon_pool_shares_rejected_total
avalon_pool_stale_total
avalon_pool_current_block_height
```

Additional pool transport counters:

```text
avalon_pool_bytes_sent_total
avalon_pool_bytes_recv_total
avalon_pool_times_sent_total
avalon_pool_times_recv_total
```

---

## 🔬 Chip-Level Telemetry (Optional)

These metrics are exported **only** when:

```bash
EXPORT_CHIP_METRICS=true
```

### Per-chip voltage (PVT_V0)

```text
avalon_chip_voltage_volts
```

Values are reported in volts (e.g. `3.03`).

### Per-chip nonce / matching-work telemetry (MW0)

```text
avalon_chip_matching_work
```

This represents **per-chip NONCE / matching-work activity**, not power.

Grafana panels consuming these metrics should be configured to **hide when no data is present**.

---

## 🌐 HTTP Endpoints

The exporter provides several HTTP endpoints:

| Endpoint | Description |
| -------- | ----------- |
| `/metrics` | Prometheus metrics (main endpoint). Accepts query parameters (they are ignored). |
| `/health` | Health check — returns `OK` and version if the poller thread is alive. |
| `/version` | JSON response with exporter version information. |
| `/debug` | JSON response with internal state for troubleshooting. **Disabled by default** — requires `ENABLE_DEBUG_ENDPOINT=true`. Returns 403 when disabled. |

**Example:**

```bash
# Health check
curl http://localhost:9100/health
# OK
# version=0.3.0

# Version info
curl http://localhost:9100/version
# {
#   "version": "0.3.0",
#   "exporter": "avalonhome-prometheus-exporter"
# }

# Debug information (requires ENABLE_DEBUG_ENDPOINT=true)
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

```text
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
No, we're not sorry.  
