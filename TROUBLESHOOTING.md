# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Avalon Home Prometheus Exporter.

**Note:** This guide assumes the exporter is running in a Docker container. Commands are shown for both `docker compose` and `docker run` deployments. If running directly (not containerized), adapt commands accordingly.

## Table of Contents

- [Common Issues](#common-issues)
- [Error Types](#error-types)
- [Performance Issues](#performance-issues)
- [Network Issues](#network-issues)
- [Debugging](#debugging)

---

## Common Issues

### Exporter won't start

**Symptoms:**
- Container exits immediately
- Error messages about configuration

**Solutions:**
1. Check environment variables are set correctly:
   ```bash
   docker compose logs avalon-exporter
   ```
2. Verify at least one of `AVALON_IP` or `AVALON_IPS` is set
3. Ensure ports are in valid range (1-65535)
4. Check `UPDATE_INTERVAL` is greater than 0

**Example error:**
```
Configuration errors:
  UPDATE_INTERVAL must be > 0, got -5
```

---

### No metrics appearing in Prometheus

**Symptoms:**
- `/metrics` endpoint returns data
- Prometheus shows no series or all series are stale

**Solutions:**
1. Verify Prometheus is scraping the exporter:
   ```yaml
   scrape_configs:
     - job_name: "avalon"
       static_configs:
         - targets: ["exporter-host:9100"]
   ```
2. Check exporter is accessible from Prometheus:
   ```bash
   curl http://exporter-host:9100/metrics
   ```
3. Verify network connectivity between Prometheus and exporter
4. Check exporter logs for errors:
   ```bash
   docker compose logs -f avalon-exporter
   ```

---

### Miners showing as down

**Symptoms:**
- `avalon_up{ip="..."} 0` in metrics
- No miner metrics appearing

**Solutions:**
1. **Check network connectivity from container:**
   ```bash
   # Test connection from inside the container
   docker compose exec avalon-exporter sh -c "echo -n 'version' | nc <miner-ip> 4028"
   
   # Or if using docker run
   docker exec avalon-exporter sh -c "echo -n 'version' | nc <miner-ip> 4028"
   
   # If using host networking, test from host:
   echo -n "version" | nc <miner-ip> 4028
   ```

2. **Verify miner API is enabled:**
   - Check miner web interface
   - Ensure CGMiner API is running on port 4028 (default)

3. **Check error metrics:**
   ```promql
   avalon_scrape_errors_timeout_total{ip="..."}
   avalon_scrape_errors_connection_refused_total{ip="..."}
   avalon_scrape_errors_network_total{ip="..."}
   ```

4. **Review exporter logs:**
   ```bash
   docker compose logs avalon-exporter | grep -i error
   ```

5. **Test direct connection from container:**
   ```bash
   # From inside the container
   docker compose exec avalon-exporter sh -c "echo -n 'version' | nc <miner-ip> 4028"
   
   # Or if using docker run
   docker exec avalon-exporter sh -c "echo -n 'version' | nc <miner-ip> 4028"
   ```

---

## Error Types

The exporter categorizes errors for better observability:

### Timeout Errors (`avalon_scrape_errors_timeout_total`)

**Causes:**
- Miner is slow to respond
- Network latency is high
- Miner is overloaded

**Solutions:**
- Increase `MINER_TIMEOUT` (default: 5.0 seconds)
- Check network conditions
- Verify miner is not overloaded

### Connection Refused (`avalon_scrape_errors_connection_refused_total`)

**Causes:**
- Miner API is not running
- Wrong port configured
- Firewall blocking connection

**Solutions:**
- Verify miner API is enabled
- Check `AVALON_PORT` matches miner configuration
- Review firewall rules

### Network Errors (`avalon_scrape_errors_network_total`)

**Causes:**
- Network unreachable
- DNS resolution failure
- Routing issues

**Solutions:**
- Verify network connectivity
- Check DNS resolution (if using hostnames)
- Review network configuration

### Parse Errors (`avalon_scrape_errors_parse_total`)

**Causes:**
- Miner returned malformed response
- Empty response from miner
- Unsupported miner firmware

**Solutions:**
- Check miner firmware version
- Verify miner is responding correctly from container:
  ```bash
  # From inside the container
  docker compose exec avalon-exporter sh -c "echo -n 'version+summary' | nc <miner-ip> 4028"
  ```
- Review exporter logs for specific error messages:
  ```bash
  docker compose logs avalon-exporter | grep -i "parse\|error"
  ```

---

## Performance Issues

### Slow Scrapes

**Symptoms:**
- High `avalon_scrape_duration_seconds` values
- Metrics appear stale

**Solutions:**
1. **Check scrape duration:**
   ```promql
   avalon_scrape_duration_seconds
   ```

2. **For multiple miners:**
   - Exporter scrapes miners in parallel (v0.2.0+)
   - Total cycle time should be ~max(individual scrape times)
   - If sequential, check logs for threading issues

3. **Optimize UPDATE_INTERVAL:**
   - Default: 10 seconds
   - Lower = more frequent updates but higher load
   - Higher = less frequent but lower load
   - Recommended: 15-30 seconds for production

4. **Check miner performance:**
   - Slow miners may indicate hardware issues
   - Review miner logs/status

### High Memory Usage

**Symptoms:**
- Container using excessive memory
- OOM (Out of Memory) kills

**Solutions:**
1. **Disable chip metrics if not needed:**
   ```bash
   EXPORT_CHIP_METRICS=false
   ```
   Chip metrics can create thousands of series per miner.

2. **Reduce UPDATE_INTERVAL:**
   - Less frequent scraping = less cached data

3. **Monitor series count:**
   ```promql
   count({__name__=~"avalon_.*"})
   ```

---

## Network Issues

### Cannot reach miners on different network

**Symptoms:**
- Exporter can't connect to miners
- Connection timeouts

**Solutions:**
1. **Use host networking (Docker):**
   ```yaml
   network_mode: host
   ```
   This allows the container to access the host's network directly.

2. **Configure Docker network:**
   - Ensure exporter and miners are on same network
   - Use `--network` flag or docker-compose network config

3. **Check firewall rules:**
   - Ensure port 4028 is accessible
   - Verify exporter can initiate outbound connections

### DNS Resolution Issues

**Symptoms:**
- Errors when using hostnames instead of IPs
- Connection failures

**Solutions:**
1. **Use IP addresses instead of hostnames:**
   ```bash
   AVALON_IP="192.168.1.50"  # Instead of "miner.local"
   ```

2. **Configure DNS in container:**
   - Add DNS servers to docker-compose
   - Or use host's DNS resolution

---

## Debugging

### Accessing the Container Shell

For interactive debugging, you can access the container shell:

```bash
# Using docker compose
docker compose exec avalon-exporter sh

# Using docker run
docker exec -it avalon-exporter sh
```

**Note:** The container uses Alpine Linux, so it has `sh` (not `bash`). Common tools available:
- `wget` (for HTTP requests)
- `nc` (netcat, for network testing)
- `ping` (if enabled in container)
- Standard Unix utilities

### Using the Debug Endpoint

The `/debug` endpoint provides internal state information:

```bash
# From host (container exposes port 9100)
curl http://localhost:9100/debug | jq

# Or from inside the container
docker compose exec avalon-exporter sh -c "wget -qO- http://localhost:9100/debug"
```

**Response includes:**
- Configuration values
- Poller heartbeat status
- Per-miner state (up/down, errors, last update)
- Scrape durations

### Using the Version Endpoint

Check exporter version:

```bash
# From host
curl http://localhost:9100/version

# Or from inside the container
docker compose exec avalon-exporter sh -c "wget -qO- http://localhost:9100/version"
```

### Enabling Debug Logging

Set log level to DEBUG for detailed information:

```bash
LOG_LEVEL=DEBUG
```

**What you'll see:**
- Individual scrape durations
- Scrape cycle timing
- Detailed error information

### Checking Exporter Health

```bash
# From host
curl http://localhost:9100/health

# Or from inside the container
docker compose exec avalon-exporter sh -c "wget -qO- http://localhost:9100/health"
```

**Expected response:**
```
OK
version=0.2.0
```

**If unhealthy:**
```
UNHEALTHY: poller heartbeat stale (last=..., now=...)
```

This indicates the poller thread has stopped or is stuck.

### Common Log Messages

**Normal operation:**
```
INFO: Poller loop started, monitoring 2 miner(s) in parallel
DEBUG: Scraped 192.168.1.50:4028 successfully in 0.234s
DEBUG: Completed scrape cycle for 2 miner(s) in 0.456s
```

**Errors:**
```
WARNING: Failed to scrape 192.168.1.50:4028 (timeout): Timeout connecting to 192.168.1.50:4028 after 5.0s
WARNING: Miner 192.168.1.50:4028 went offline
```

---

## Getting Help

If you're still experiencing issues:

1. **Check the logs:**
   ```bash
   docker compose logs avalon-exporter
   ```

2. **Collect debug information:**
   ```bash
   # From host
   curl http://localhost:9100/debug > debug.json
   curl http://localhost:9100/metrics > metrics.txt
   
   # Or from inside container (if needed)
   docker compose exec avalon-exporter sh -c "wget -qO- http://localhost:9100/debug" > debug.json
   ```

3. **Review error metrics:**
   - Check Prometheus for error type breakdowns
   - Look for patterns in error timing

4. **Open an issue:**
   - Include exporter version
   - Include relevant log excerpts
   - Include debug endpoint output (sanitize IPs if needed)
   - Describe your configuration

