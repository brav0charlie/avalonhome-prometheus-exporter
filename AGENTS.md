# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

A Prometheus exporter for Avalon Home-series ASIC miners (Nano 3S, Mini 3). It polls miners via the CGMiner TCP API and exposes metrics on an HTTP endpoint. Pure Python, zero dependencies (stdlib only), single-file application.

## Architecture

The entire exporter lives in `app/exporter.py` (~600 lines). Key components:

- **Configuration** — Environment variables parsed at module level (`AVALON_IP`/`AVALON_IPS`, `AVALON_PORT`, `UPDATE_INTERVAL`, `EXPORTER_PORT`, `EXPORT_CHIP_METRICS`, `MINER_TIMEOUT`, `LOG_LEVEL`). Validated at startup via `validate_configuration()`.
- **Poller thread** — Background thread scrapes all miners in parallel every `UPDATE_INTERVAL` seconds using a combined CGMiner TCP command (`version+summary+stats+config+devs+devdetails+pools`). Results are stored in module-level dicts (`latest_metrics`, `latest_pools`, `latest_chips`, etc.).
- **HTTP server** — `http.server.HTTPServer` with `MetricsHandler` serving `/metrics`, `/health`, `/version`, and `/debug` endpoints.
- **Shared state** — Module-level dicts keyed by miner IP hold metrics, pool data, chip data, version info, error state, and counters. The poller writes, the HTTP handler reads.
- **Metric formatting** — Prometheus text format is assembled manually in the request handler (no client library).

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
