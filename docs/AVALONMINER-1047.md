# AvalonMiner 1047 support

This note documents the sanitized AvalonMiner 1047 contract used for parser
coverage. It does not include raw miner payloads, DNA values, MAC addresses,
pool URLs, account names, worker names, or private timestamps.

Validated target shape:

- Model/product: `AvalonMiner 1047`
- CGMiner: `4.11.1`
- CGMiner API: `3.7`
- API port: `4028`
- Hash boards: `2`
- Read-only commands used by the exporter:
  `version+summary+stats+config+devs+devdetails+pools`

Additional 1047 mappings:

| Source field | Metric | Unit / behavior |
|---|---|---|
| `Temp` | `avalon_temp_current_celsius` | Celsius |
| `Fan2` | `avalon_fan2_rpm` | RPM |
| `SYSTEMSTATU` | `avalon_system_working` | 1 when the status contains `In Work` |
| `SYSTEMSTATU` | `avalon_hash_boards` | Parsed from `Hash Board: <n>` |
| `MHS 30s` | `avalon_hashrate_ghs` | Converted from MH/s to GH/s when `GHSspd` is absent |
| `MHS 1m` | `avalon_hashrate_1m_ghs` | Converted from MH/s to GH/s |
| `MHS 5m` | `avalon_hashrate_5m_ghs` | Converted from MH/s to GH/s |
| `MHS 15m` | `avalon_hashrate_15m_ghs` | Converted from MH/s to GH/s |
| `PVT_T0`, `PVT_T1` | chip temperature aggregates | Combined across hash boards |
| `PVT_V0`, `PVT_V1` | chip voltage aggregates | Combined across hash boards, raw values divided by 100 |
| `MW0`, `MW1` | chip matching-work aggregates | Combined across hash boards |

Power fields remain firmware-defined unless model-specific units are verified.
