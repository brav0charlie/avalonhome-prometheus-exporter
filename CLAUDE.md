# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Prometheus exporter for Avalon Home-series ASIC miners (Nano 3S, Mini 3). It polls miners via the CGMiner TCP API and exposes metrics on an HTTP endpoint. Pure Python, zero dependencies (stdlib only), single-file application.

## Architecture

The entire exporter lives in `app/exporter.py`. Key components:

- **Configuration** — Environment variables parsed at module level (`AVALON_IP`/`AVALON_IPS`, `AVALON_PORT`, `UPDATE_INTERVAL`, `EXPORTER_PORT`, `EXPORT_CHIP_METRICS`, `MINER_TIMEOUT`, `LOG_LEVEL`, `ENABLE_DEBUG_ENDPOINT`). Target list construction and validation are deferred to `build_targets()`, which is called from `main()`. This means the module can be imported without `AVALON_IP`/`AVALON_IPS` set — `TARGETS` starts as an empty list and is populated at runtime.
- **Poller thread** — Background thread scrapes all miners in parallel every `UPDATE_INTERVAL` seconds using a `ThreadPoolExecutor` (capped at `min(len(TARGETS), 32)` workers). The executor is created once before the poll loop and shut down in a `finally` block. Per-cycle waiting uses `as_completed()` with a `MINER_TIMEOUT * 2` timeout. A combined CGMiner TCP command (`version+summary+stats+config+devs+devdetails+pools`) is used per scrape.
- **HTTP server** — `http.server.HTTPServer` with `AvalonHandler` serving `/metrics`, `/health`, `/version`, and `/debug` endpoints. HTTP path routing strips query parameters via `urlparse` so `/metrics?target=foo` routes correctly. The `/debug` endpoint is gated behind the `ENABLE_DEBUG_ENDPOINT` env var (default: off) and returns 403 when disabled.
- **Shared state** — Module-level dicts keyed by miner IP hold metrics, pool data, chip data, version info, error state, and counters. The poller writes, the HTTP handler reads. All shared state access (including `poller_last_heartbeat`) is synchronized via `metrics_lock`.
- **Metric formatting** — Prometheus text format is assembled manually in the request handler (no client library). All metric families have `# HELP` and `# TYPE` annotations. Static metadata is defined in two module-level dicts: `MINER_METRIC_META` (miner-level metrics) and `POOL_METRIC_META` (pool-level metrics). Dynamic metrics like `avalon_ps_slot_*` are annotated via `startswith` fallback logic.

## Parsing Architecture

- **`parse_all_bracket(text)`** — Single-pass regex extracting all `KEY[value]` pairs into a dict. Used at the top of `_parse_miner_metrics` and `_parse_chip_metrics` for O(1) lookups against `stats0`.
- **`parse_all_kv(text)`** — Single-pass regex extracting all `key=value` pairs into a dict. Used for `stats0` and `summary_section` in `_parse_miner_metrics`.
- **`find_bracket` / `find_kv`** — Per-key regex helpers. Still used in other parsing contexts: combined response splitting (`split_combined_response`), version extraction (`extract_version_info_from_section`), and pool index parsing (`pool_index_from_id`). These are not hot-path functions.

## Safety and Defensive Coding

- **Label value truncation** — `_escape_label_value()` truncates Prometheus label values to `MAX_LABEL_VALUE_LENGTH` (128 chars) after escaping to prevent cardinality explosion from misbehaving firmware.
- **Hostname validation** — `validate_hostname()` validates IPv4 (via `inet_aton`), IPv6 including bracket-wrapped (via `inet_pton`), and RFC-compliant hostnames (label rules, 253-char limit).
- **Content-Length** — The `/metrics` response body is encoded to bytes before calculating `Content-Length` to avoid mismatch when replacement characters are present.

## Build & Run

```bash
# Run locally (requires env vars set, e.g. AVALON_IP)
python app/exporter.py

# Docker build
docker build -t avalonhome-prometheus-exporter .

# Docker Compose (uses .env file)
cp .env.example .env  # edit with your miner IPs
docker compose up -d

# View logs
docker compose logs -f avalonhome-exporter
```

There are no tests, no linter config, and no package manager — it's a single Python file with no third-party dependencies.

## CI/CD

GitHub Actions workflow (`.github/workflows/docker.yml`) builds multi-arch Docker images (amd64/arm64) and pushes to `ghcr.io/brav0charlie/avalonhome-prometheus-exporter` on release publish or manual dispatch.

## Key Files

- `app/exporter.py` — The entire application
- `grafana/avalonhome-miner-dashboard.json` — Pre-built Grafana dashboard
- `FIELDS-README.md` — Maps raw CGMiner API fields to Prometheus metric names
- `DEPLOYMENT.md` — Production deployment guide
- `TROUBLESHOOTING.md` — Debugging guide

## Version

The exporter version is defined in `app/exporter.py` as `__version__` and must also be updated in `docker-compose.yml` (image tag) when releasing.
