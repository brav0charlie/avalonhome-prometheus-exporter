# Avalon Home Prometheus Exporter Quick Reference

Use this file for common commands, workflows, naming conventions, safety
boundaries, and completion checklists. `GIT_STANDARDS.md` is authoritative for
version control, signing, attribution, pull requests, and releases. Project
architecture and agent guidance live in `AGENTS.md`; metric semantics live in
`docs/FIELDS-README.md`; deployment and operational guidance live in
`docs/DEPLOYMENT.md` and `docs/TROUBLESHOOTING.md`.

## Repository Workflow

- Host: GitHub; follow GitHub Flow as defined in `GIT_STANDARDS.md`.
- Keep `main` releasable; every change uses a short-lived branch and pull
  request.
- Branch format: `type/short-kebab-description`.
- Allowed branch types: `feat`, `fix`, `hotfix`, `chore`, `docs`, `refactor`,
  `perf`, `test`, `build`, `ci`, and `release`.
- Use `release/vX.Y.Z` for version and changelog preparation.
- Do not add a `codex/` prefix. AI attribution belongs in commits and pull
  requests as specified by `GIT_STANDARDS.md`, not branch names.
- Use Conventional Commit summaries in imperative mood; keep the subject at
  50 characters or fewer when possible and never exceed 72.
- Sign commits and tags with the configured developer identity.
- Pull requests target `main` and are reviewed manually before merge.
- Always squash merge, then delete the merged branch locally and remotely.
- Review `git status`, `git diff`, and the exact staged diff. Never use
  `git add .` blindly.
- Preserve unrelated work in a dirty worktree; never discard it to make a
  task easier.

## History Records

- `history/tasks/` holds concise task briefs: goal, acceptance criteria, hard
  constraints, out-of-scope work, and related ADRs.
- `history/logs/` records what changed, actual validation, SemVer impact, files
  touched, and the next recommended step.
- `history/decisions/` holds architecture decision records with context,
  alternatives, consequences, and implementation notes.
- Start new records from the corresponding `TEMPLATE.md`; do not overwrite the
  templates.
- Link tasks, logs, ADRs, and pull requests where applicable so future agents
  can recover both the implementation history and the reasoning.

## Project Shape

- `app/exporter.py` contains the complete runtime application.
- The project is Python standard-library only; do not add a dependency or
  package manager without an explicit architectural decision.
- The container runtime is Python 3.12 on Alpine and runs as UID/GID 1000.
- Configuration is read from environment variables at module import; target
  validation is deferred to `build_targets()` in `main()`.
- Each miner is queried once per poll with the read-only combined command:
  `version+summary+stats+config+devs+devdetails+pools`.
- A persistent `ThreadPoolExecutor` scrapes miners in parallel, capped at 32
  workers.
- Shared miner state is protected by `metrics_lock`.
- `ThreadingHTTPServer` exposes `/metrics`, `/health`, `/version`, and the
  opt-in `/debug` endpoint.
- Prometheus text exposition is assembled manually; there is no client
  library.

## Common Commands

Run locally:

```sh
AVALON_IP=192.168.1.50 python3 app/exporter.py
```

Run all tests:

```sh
python3 --version  # Must report Python 3.12.x.
python3 -m unittest discover -s tests -v
```

Compile-check Python:

```sh
python3 -m compileall -q app tests
```

Check patch whitespace:

```sh
git diff --check
```

Build the container:

```sh
docker build -t avalonhome-prometheus-exporter .
```

Run with Compose:

```sh
[ -e .env ] || cp .env.example .env
# Edit .env with the miner address or addresses.
docker compose up -d
docker compose logs -f avalonhome-exporter
```

Check runtime endpoints:

```sh
curl --fail http://localhost:9100/health
curl --fail http://localhost:9100/version
curl --fail http://localhost:9100/metrics
```

## Configuration

| Variable | Purpose | Application default |
|---|---|---|
| `AVALON_IP` | Single miner hostname or IP | Required unless `AVALON_IPS` is set |
| `AVALON_IPS` | Comma-separated miner targets | Required unless `AVALON_IP` is set |
| `AVALON_PORT` | CGMiner TCP API port | `4028` |
| `UPDATE_INTERVAL` | Poll interval in seconds | `10` (`15` in Docker defaults/examples) |
| `EXPORTER_PORT` | HTTP listen port | `9100` |
| `MINER_TIMEOUT` | Miner TCP timeout in seconds | `5.0` |
| `EXPORT_CHIP_METRICS` | Enable per-chip series | `false` |
| `ENABLE_DEBUG_ENDPOINT` | Enable `/debug` | `false` |
| `LOG_LEVEL` | Python log level | `INFO` |

`AVALON_IPS` takes precedence when both target variables are set. Hostnames,
IPv4, IPv6, port ranges, positive timeouts, and positive poll intervals are
validated at startup.

## Parser And Metric Rules

- Treat miner payloads as firmware- and model-dependent input.
- Require `version`, `summary`, `stats`, and `pools` sections plus `STATS=0`;
  incomplete responses are scrape failures.
- Preserve existing field precedence and unit conversions. For example,
  `GHSspd` wins over the converted summary `MHS 30s` fallback.
- Never infer units for undocumented power fields. `MPO` and `PS[...]` values
  remain firmware-defined unless model-specific evidence establishes a scale.
- Export the `ITemp=-273` sentinel as reported; dashboards decide whether to
  filter it.
- Keep every emitted miner or pool metric documented with `# HELP` and
  `# TYPE` metadata.
- Update `docs/FIELDS-README.md` whenever raw-field mappings, units, fallbacks,
  or metric names change.
- Update the Grafana dashboard when a metric rename or semantic change affects
  an existing query.
- Bound labels with `_escape_label_value()` and avoid adding unbounded label
  dimensions.
- Per-chip metrics remain off by default because of cardinality. Aggregate
  chip metrics remain available when the raw arrays exist.
- On scrape failure, cached samples are deliberately dropped so Prometheus
  marks them stale; keep availability and error metrics visible.

## Safety And Privacy

- Miner communication must remain read-only unless a separate, explicitly
  approved feature changes that policy.
- Do not add configuration-changing or power-control CGMiner commands to the
  scrape path.
- Keep the 1 MiB response limit and socket timeouts unless evidence supports a
  carefully reviewed change.
- Never commit unsanitized miner payloads containing DNA values, MAC addresses,
  pool URLs, account or worker names, private IPs, or private timestamps.
- Keep `/debug` disabled by default. It exposes miner addresses, errors, and
  internal state and must not be publicly reachable.
- The exporter requires outbound miner access on TCP 4028 and inbound
  Prometheus access on the exporter port; it should not be internet-exposed.

## Testing Expectations

- Add sanitized `unittest` coverage for new parsing behavior and regressions.
- Cover valid values, missing fields, malformed or unknown values, fallbacks,
  conversions, and model compatibility where relevant.
- Prefer testing the public parsing result or emitted metric behavior, not only
  a helper in isolation.
- Run the complete test suite after changing shared parser helpers.
- Use Python 3.12 for release validation. The macOS system Python may be older
  than the runtime syntax supported by this project.
- There is currently no pull-request CI test job; local validation is required
  before approval or merge.

## Operational Semantics

- `/health` reports whether the exporter HTTP server and poller heartbeat are
  healthy. It does not mean every miner is reachable.
- `avalon_up` reports the latest scrape result per miner.
- A failed miner scrape removes cached miner, pool, and chip samples while
  retaining status, error counters, and last-success information.
- The `/debug` endpoint returns HTTP 403 unless explicitly enabled.
- Query parameters are ignored for route matching, so `/metrics?...` still
  resolves to `/metrics`.
- Pool labels can change when firmware changes URL, priority, status, or ID;
  account for that when writing PromQL aggregations.

## Review And Reporting Patterns

- For code review, lead with actionable findings ordered by severity and use
  precise file and line references.
- If there are no findings, say so directly and state remaining test gaps or
  hardware-dependent risk.
- For diagnostics, identify the cause and evidence before proposing a change.
- When reporting validation, name the command intent and meaningful pass/fail
  result; do not rely on unstated terminal output.
- Do not edit during an audit unless the request explicitly includes fixing or
  implementation.

## Versioning And Release

The release version uses SemVer. Runtime values omit the `v` prefix; Docker
tags, Git tags, and release headings include it. Full release and signing rules
live in `GIT_STANDARDS.md`.

Update these current-version references for a release:

- `app/exporter.py`: `__version__ = "X.Y.Z"`
- `docker-compose.yml`: image tag `vX.Y.Z`
- `README.md`: exporter metric, health, and version endpoint examples
- `docs/TROUBLESHOOTING.md`: expected health response
- `CHANGELOG.md`: add a new `## [vX.Y.Z] - YYYY-MM-DD` section and release link
- GitHub release/tag: signed, annotated `vX.Y.Z`

Do not replace historical version headings, release links, or compatibility
notes. The GitHub Actions release workflow publishes both the selected version
tag and `latest` as multi-architecture images for amd64 and arm64.

## Completion Checklist

- Confirm the branch follows `type/short-kebab-description`, uses an allowed
  type from `GIT_STANDARDS.md`, and is not `main`.
- Read the relevant docs before changing parser, metric, dashboard, deployment,
  or release behavior.
- Keep the stdlib-only architecture unless a dependency is explicitly approved.
- Add or update sanitized tests for behavior changes.
- Update metric metadata and `docs/FIELDS-README.md` for metric changes.
- Check Grafana queries for metric renames or semantic changes.
- Run `python3 -m unittest discover -s tests -v` with Python 3.12.
- Run `python3 -m compileall -q app tests`.
- Run `git diff --check`.
- Verify current version references when preparing a release.
- Review `git diff` and `git status` for unintended or unrelated changes.
- Stage only explicit files, then review `git diff --staged` before committing.
- Preserve the configured AI attribution and cryptographic signing behavior.
- Let the maintainer review and merge the pull request manually.
