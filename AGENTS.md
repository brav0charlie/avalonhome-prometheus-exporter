# AGENTS.md

This file is the shared repository guidance for AI coding assistants. Read it
before making changes, then use `QUICKREF.md` for common commands and
`GIT_STANDARDS.md` for the binding version-control workflow.

## Project Overview

This repository contains a Prometheus exporter for Avalon ASIC miners,
including the Nano 3S, Mini 3, and AvalonMiner 1047. It polls the CGMiner TCP
API and exposes miner telemetry over HTTP.

The application is pure Python 3.12 and has no third-party runtime
dependencies. The exporter is implemented in `app/exporter.py`; sanitized
unit tests live in `tests/`.

## Sources of Truth

- `GIT_STANDARDS.md` — required branching, commit, signing, attribution, pull
  request, changelog, and release practices.
- `QUICKREF.md` — project commands, architecture summary, safety boundaries,
  testing expectations, and release checklist.
- `docs/FIELDS-README.md` — canonical raw CGMiner field-to-metric mapping.
- `docs/AVALONMINER-1047.md` — sanitized AvalonMiner 1047 parser contract and
  compatibility notes.
- `docs/DEPLOYMENT.md` and `docs/TROUBLESHOOTING.md` — deployment and operator
  guidance.
- `history/` — durable task, decision, and session records; use the templates
  in each subdirectory.

Do not duplicate detailed metric semantics in this file. Update the canonical
field documentation when parser behavior changes.

## Architecture

The exporter is a single-file application with these major areas:

- **Configuration** — environment variables are parsed at module import time,
  but target construction and validation are deferred to `build_targets()` and
  `main()`. This permits importing the module in tests without setting
  `AVALON_IP` or `AVALON_IPS`.
- **Miner transport** — `query_miner()` connects to the CGMiner TCP API and
  sends the combined command
  `version+summary+stats+config+devs+devdetails+pools`. Response size is
  bounded by `MAX_RESPONSE_SIZE`.
- **Parsing** — `split_combined_response()` separates command sections.
  `_parse_miner_metrics()`, `_parse_chip_metrics()`, and
  `_parse_pool_metrics()` convert the response into metric dictionaries.
  `parse_all_bracket()` and `parse_all_kv()` provide single-pass hot-path
  lookups.
- **Polling** — `poller_loop()` reuses a `ThreadPoolExecutor`, capped at 32
  workers, to scrape configured miners concurrently every `UPDATE_INTERVAL`.
- **Shared state** — module-level dictionaries keyed by miner IP hold the most
  recent metrics, pools, chips, version data, errors, and counters. All reads
  and writes, including the poller heartbeat, must remain protected by
  `metrics_lock`.
- **HTTP serving** — `ThreadingHTTPServer` uses `AvalonHandler` to serve
  `/metrics`, `/health`, `/version`, and the opt-in `/debug` endpoint. Routing
  uses `urlparse()` so query parameters do not change endpoint matching.
- **Prometheus output** — text exposition is assembled without a client
  library. Preserve the `# HELP` and `# TYPE` metadata for every metric family.

## Parser and Safety Invariants

- `ENABLE_DEBUG_ENDPOINT` defaults to false because `/debug` exposes miner IPs
  and internal error state.
- Prometheus label values are escaped and truncated to
  `MAX_LABEL_VALUE_LENGTH`; do not bypass `_escape_label_value()`.
- Continue validating IPv4, IPv6, and RFC-compliant hostnames before polling.
- Calculate HTTP `Content-Length` from the encoded response bytes.
- Treat unknown `SYSTEMSTATU` work states as unknown: omit
  `avalon_system_working` instead of guessing a value.
- Preserve the `GHSspd` preference for `avalon_hashrate_ghs`; use summary
  `MHS 30s` only as the documented fallback and convert MH/s to GH/s.
- Scan board-indexed `PVT_T*`, `PVT_V*`, and `MW*` arrays from suffix 0 through
  15 in numeric order before calculating chip aggregates or labels.
- Per-chip series remain opt-in through `EXPORT_CHIP_METRICS`; aggregate chip
  metrics are emitted whenever source arrays are available.
- Never commit real miner responses, pool credentials, MAC addresses, DNA
  identifiers, public IPs, or other identifying telemetry. Tests and history
  records must use synthetic or redacted fixtures.

## Build, Run, and Test

```bash
# Run locally (set exactly one of AVALON_IP or AVALON_IPS first)
python3 app/exporter.py

# Run the complete test suite
python3 -m unittest discover -s tests -v

# Compile-check application and tests
python3 -m compileall -q app tests

# Docker build
docker build -t avalonhome-prometheus-exporter .

# Docker Compose
cp .env.example .env
docker compose up -d

# View logs
docker compose logs -f avalonhome-exporter
```

There is currently no package manager or linter configuration. Do not add a
third-party dependency for behavior that the standard library handles cleanly.

## CI/CD

`.github/workflows/docker.yml` builds and publishes amd64/arm64 images to
`ghcr.io/brav0charlie/avalonhome-prometheus-exporter` when a GitHub release is
published or the workflow is manually dispatched. It publishes both the
selected version tag and `latest`.

## Versioning

For a release, review all current-version references and update at least:

- `app/exporter.py` — `__version__ = "X.Y.Z"`
- `docker-compose.yml` — image tag `vX.Y.Z`
- `README.md` and `docs/TROUBLESHOOTING.md` — user-facing examples
- `CHANGELOG.md` — release section and comparison links

Preserve historical version references. Release tags use signed, annotated
`vX.Y.Z` tags as required by `GIT_STANDARDS.md`.
