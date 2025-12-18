# Changelog

All notable changes to this project will be documented in this file.

This project follows semantic versioning: https://semver.org/

## [v0.1.2] - 2025-12-18

### Fixed
- Corrected per-chip series ordering in Grafana by zero-padding chip index labels to three digits (`001`, `002`, …). This ensures numeric ordering instead of lexicographic ordering (for example, `1, 10, 2`).

### Notes
- This change updates the `chip` label format for per-chip metrics (for example, `chip="001"` instead of `chip="1"`).
- Any Grafana dashboards, panel overrides, variables, or alerts that reference specific chip label values must be updated accordingly.
- Three-digit padding was chosen to support potential future miners with higher chip counts (e.g. Avalon Q series).

[v0.1.2]: https://github.com/brav0charlie/avalonhome-prometheus-exporter/releases/tag/v0.1.2



## [v0.1.1] - 2025-12-17

### Fixed
- Prevented stale miner telemetry from being continuously exported when a miner becomes unreachable. On scrape failures, cached per-miner metrics are now dropped so Prometheus correctly marks the series as stale.
- Resolved an issue where Grafana dashboards could appear to show miners online and reporting constant values throughout downtime due to cached exporter state.
- Ensured miner downtime is accurately reflected as gaps in time-series panels rather than flat “last known value” lines.

### Notes
- Availability and health metrics (`avalon_up`, `avalon_last_scrape_timestamp_seconds`, and downtime counters) continue to be exported during miner outages for visibility and alerting.
- This change affects exporter behavior only and does not modify metric names, labels, or units.
- Recommended for all users running Grafana dashboards that rely on visual gap detection for miner outages.

[v0.1.1]: https://github.com/brav0charlie/avalonhome-prometheus-exporter/releases/tag/v0.1.1



## [v0.1.0] - 2025-12-16

### Added
- Initial public release of **avalon-prometheus-exporter**
- Support for Avalon A3-series miners via the CGMiner TCP API (tested with Nano 3S and Mini 3)
- Multi-miner support via `AVALON_IPS` (comma-separated) or single miner via `AVALON_IP`
- Prometheus `/metrics` endpoint exporting miner telemetry collected from CGMiner commands:
  - `version`
  - `summary`
  - `stats`
  - `config`
  - `devs`
  - `devdetails`
  - `pools`
- Automatic model, firmware, and hardware identification via `version`
- Per-miner availability and health metrics:
  - Up/down state
  - Last scrape timestamp
  - Down-duration tracking
  - Scrape error counters
  - Status transition counters (up/down changes)
- Hashrate metrics reported in GHS with guidance for TH/s conversion (`/ 1000`)
- Temperature metrics including inlet, outlet, average, maximum, and target temperatures
- Fan RPM and fan duty-cycle metrics
- Hardware error counters and derived error-rate metrics
- Share and block statistics, including best share tracking
- Per-pool metrics indexed by pool number:
  - Pool availability
  - Accepted, rejected, and stale shares
  - Pool difficulty and current block height
  - Pool transport counters (send/receive bytes and message counts)
- Optional extended telemetry gated behind `EXPORT_CHIP_METRICS`:
  - Per-chip voltage telemetry derived from `PVT_V0`
  - Per-chip matching-work / nonce telemetry derived from `MW0`
- Power and board-level telemetry where available:
  - MPO target
  - Raw PSU slot values
  - Decoded voltage, current, and power fields when present
- Grafana dashboard JSON included:
  - Miner and pool selection via Prometheus variables
  - Hashrate, temperature, fan, pool, and power visualizations
  - Chip-level panels that automatically hide when chip metrics are disabled
- Docker support:
  - Single lightweight image (Python 3.12 Alpine)
  - Non-root runtime user
  - Configurable exporter and poll intervals via environment variables
- Documentation:
  - Quickstart instructions
  - Environment variable reference
  - Metric overview and Grafana dashboard guidance

### Notes
- This is the first public release of the project
- Metric names use the `avalon_` prefix exclusively
- Chip-level metrics are disabled by default to avoid unnecessary cardinality
- The exporter health endpoint reflects exporter availability, not miner reachability

[v0.1.0]: https://github.com/brav0charlie/avalonhome-prometheus-exporter/releases/tag/v0.1.0
