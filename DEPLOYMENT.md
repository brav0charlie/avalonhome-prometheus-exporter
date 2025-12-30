# Deployment Guide

Best practices for deploying the Avalon Home Prometheus Exporter in production.

## Table of Contents

- [Docker Deployment](#docker-deployment)
- [Systemd Service](#systemd-service)
- [Performance Tuning](#performance-tuning)
- [Monitoring the Exporter](#monitoring-the-exporter)
- [Security Considerations](#security-considerations)

---

## Docker Deployment

### Basic Docker Run

```bash
docker run -d \
  --name avalon-exporter \
  --network host \
  --restart unless-stopped \
  -e AVALON_IPS="192.168.1.50,192.168.1.51" \
  -e AVALON_PORT=4028 \
  -e UPDATE_INTERVAL=15 \
  -e EXPORTER_PORT=9100 \
  -e MINER_TIMEOUT=5.0 \
  -e LOG_LEVEL=INFO \
  ghcr.io/brav0charlie/avalonhome-prometheus-exporter:latest
```

### Docker Compose

See `docker-compose.yml` for a complete example. Key points:

- Use `network_mode: host` to access miners on your LAN
- Set `restart: unless-stopped` for automatic recovery
- Configure via `.env` file for easier management

### Resource Limits

Recommended resource limits:

```yaml
services:
  avalon-exporter:
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.5'
        reservations:
          memory: 64M
          cpus: '0.25'
```

**Note:** Memory usage depends on:
- Number of miners
- Whether chip metrics are enabled
- Scrape interval

---

## Systemd Service

For bare metal or VM deployments:

```ini
[Unit]
Description=Avalon Home Prometheus Exporter
After=network.target

[Service]
Type=simple
User=prometheus
Group=prometheus
ExecStart=/usr/bin/python3 /opt/avalon-exporter/app/exporter.py
Environment="AVALON_IPS=192.168.1.50,192.168.1.51"
Environment="AVALON_PORT=4028"
Environment="UPDATE_INTERVAL=15"
Environment="EXPORTER_PORT=9100"
Environment="LOG_LEVEL=INFO"
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Save to `/etc/systemd/system/avalon-exporter.service`, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable avalon-exporter
sudo systemctl start avalon-exporter
```

---

## Performance Tuning

### Scrape Interval

**Recommendations:**
- **Development/Testing:** 10-15 seconds
- **Production:** 15-30 seconds
- **High-frequency monitoring:** 5-10 seconds (increases load)

**Considerations:**
- Lower intervals = more accurate real-time data but higher CPU/network usage
- Higher intervals = less load but less frequent updates
- Miner API can handle frequent requests, but network conditions matter

### Timeout Configuration

**Default:** `MINER_TIMEOUT=5.0` seconds

**When to increase:**
- Slow network connections
- High latency to miners
- Miners that are slow to respond

**When to decrease:**
- Fast local network
- Want faster failure detection

**Example:**
```bash
MINER_TIMEOUT=10.0  # For slow connections
```

### Chip Metrics

**Impact:**
- Enabling `EXPORT_CHIP_METRICS=true` creates many additional series
- Per miner: ~3 * chip_count additional metrics
- Example: 100 chips = ~300 additional series per miner

**Recommendations:**
- **Disable** for production monitoring (default)
- **Enable** only when debugging chip-level issues
- Monitor Prometheus series count if enabled

### Parallel Scraping

**Behavior (v0.2.0+):**
- Miners are scraped in parallel using threads
- Total cycle time ≈ max(individual scrape times)
- Significantly faster for multiple miners

**Example:**
- 3 miners, each takes 0.5s
- Sequential: ~1.5s total
- Parallel: ~0.5s total

**No configuration needed** - automatic for multiple miners.

---

## Monitoring the Exporter

### Key Metrics to Monitor

**Exporter Health:**
```promql
# Exporter version
avalon_exporter_info

# Poller heartbeat (via health endpoint)
up{job="avalon-exporter"}
```

**Scrape Performance:**
```promql
# Scrape duration per miner
avalon_scrape_duration_seconds

# Average scrape duration
avg(avalon_scrape_duration_seconds)

# Scrape cycle time (if multiple miners)
# Check logs for "Completed scrape cycle" messages
```

**Error Rates:**
```promql
# Total errors
rate(avalon_scrape_errors_total[5m])

# By error type
rate(avalon_scrape_errors_timeout_total[5m])
rate(avalon_scrape_errors_connection_refused_total[5m])
rate(avalon_scrape_errors_network_total[5m])
rate(avalon_scrape_errors_parse_total[5m])
```

**Miner Availability:**
```promql
# Miners currently up
sum(avalon_up)

# Miners down
count(avalon_up == 0)

# Uptime percentage
avg(avalon_up) * 100
```

### Recommended Alerts

```yaml
groups:
  - name: avalon_exporter
    rules:
      - alert: AvalonExporterDown
        expr: up{job="avalon-exporter"} == 0
        for: 1m
        annotations:
          summary: "Avalon exporter is down"

      - alert: AvalonExporterHighErrorRate
        expr: rate(avalon_scrape_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High scrape error rate"

      - alert: AvalonExporterSlowScrapes
        expr: avalon_scrape_duration_seconds > 10
        for: 5m
        annotations:
          summary: "Slow scrape duration detected"

      - alert: AvalonMinerDown
        expr: avalon_up == 0
        for: 2m
        annotations:
          summary: "Miner {{ $labels.ip }} is down"
```

---

## Security Considerations

### Network Security

1. **Firewall Rules:**
   - Exporter only needs **outbound** access to miners (port 4028)
   - Prometheus needs **inbound** access to exporter (port 9100)
   - Restrict access to exporter port to Prometheus only

2. **Network Isolation:**
   - Run exporter on same network segment as miners when possible
   - Use VPN/tunnels for remote miners
   - Avoid exposing exporter to public internet

### Container Security

1. **Non-root User:**
   - Exporter runs as UID/GID 1000 (non-root)
   - No privileged capabilities needed

2. **Read-only Filesystem:**
   ```yaml
   securityContext:
     readOnlyRootFilesystem: true
     runAsNonRoot: true
     runAsUser: 1000
   ```

3. **Resource Limits:**
   - Set memory/CPU limits to prevent resource exhaustion
   - See [Resource Limits](#resource-limits) section

### Secrets Management

**Environment Variables:**
- No sensitive data required (miners don't use authentication)
- If using secrets manager, inject via environment variables

**Example (Kubernetes):**
```yaml
env:
  - name: AVALON_IPS
    valueFrom:
      secretKeyRef:
        name: avalon-config
        key: miner-ips
```

---

## High Availability

### Multiple Exporters

**When to use:**
- Very large number of miners (>20)
- Geographic distribution
- Redundancy requirements

**Configuration:**
- Split miners across multiple exporter instances
- Use different `AVALON_IPS` per instance
- Label exporters in Prometheus for identification

**Example:**
```yaml
# Exporter 1
AVALON_IPS="miner1,miner2,miner3"

# Exporter 2
AVALON_IPS="miner4,miner5,miner6"
```

### Load Distribution

- Each exporter handles its assigned miners independently
- No coordination needed between exporters
- Prometheus scrapes all exporters

---

## Backup and Recovery

### Configuration Backup

**Important files:**
- `.env` or environment configuration
- `docker-compose.yml` (if used)
- Kubernetes manifests (if used)

**Backup strategy:**
- Version control for configuration
- Regular backups of deployment configs

### Data Recovery

**No persistent data:**
- Exporter is stateless
- All metrics are in Prometheus
- Restarting exporter doesn't lose data

**Recovery steps:**
1. Restore configuration
2. Restart exporter
3. Verify metrics resume

---

## Troubleshooting Deployment Issues

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting guidance.

**Quick checks:**
1. Verify exporter is running: `docker ps` or `kubectl get pods`
2. Check logs: `docker logs avalon-exporter` or `kubectl logs <pod>`
3. Test health: `curl http://localhost:9100/health`
4. Verify metrics: `curl http://localhost:9100/metrics`

