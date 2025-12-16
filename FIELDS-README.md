# FIELDS-README.md

This document explains the **raw fields** reported by Avalon Home-series miners via the CGMiner TCP API
and how they are interpreted and exported by `app/exporter.py`.

It is a reference for:
- Understanding metric semantics
- Debugging unexpected values
- Extending the exporter or dashboards
- Avoiding misinterpretation of low-level telemetry

The exporter uses a **single combined request** per scrape:

- `version+summary+stats+config+devs+devdetails+pools`

> Notes:
> - Values are exported **as-is** unless explicitly stated.
> - Some fields are model/firmware dependent (Nano 3S vs Mini 3).
> - Some fields may report placeholder/sentinel values (e.g. `ITemp=-273` on some Nano 3S firmware).
> - Per-chip metrics are exported only when `EXPORT_CHIP_METRICS=true`.

---

## 1) How the exporter maps raw fields to Prometheus metrics

For each miner (label `ip="..."`), the exporter emits:
- Core scrape health metrics (`avalon_up`, timestamps, error counters)
- Miner-level metrics derived from `summary` and `stats` (STATS=0)
- Pool metrics derived from `pools` and `stats` pool segments (STATS=1..N with `ID=POOLx`)
- Optional per-chip series derived from `PVT_T0`, `PVT_V0`, and `MW0`
- A static info metric `avalon_info{...} 1` derived from `version`

---

## 2) Exporter health & scrape state (not miner fields)

These are produced by the exporter itself:

- `avalon_up` — 1 if last scrape succeeded, else 0
- `avalon_last_scrape_timestamp_seconds` — unix time of last successful scrape
- `avalon_down_duration_seconds` — seconds since last successful scrape (when down)
- `avalon_scrape_errors_total` — scrape failures counter
- `avalon_status_changes_total` — number of UP↔DOWN transitions
- `avalon_status_ups_total` — number of transitions to UP
- `avalon_status_downs_total` — number of transitions to DOWN

---

## 3) `version` command fields (static identity)

The exporter parses the `VERSION,...` record and exports:

### `avalon_info{...} 1`

Labels come from these raw keys:

- `MODEL` → `model`
- `PROD` → `prod`
- `LVERSION` (fallback: `CGVERSION`) → `firmware`
- `CGMiner` → `cgminer`
- `API` → `api`
- `HWTYPE` → `hwtype`
- `SWTYPE` → `swtype`
- `DNA` → `dna`
- `MAC` → `mac`

---

## 4) `summary` command fields (session counters & percentages)

### Uptime
- `Elapsed` — seconds since cgminer started  
  Exported as: `avalon_uptime_seconds`

### Shares / blocks / best share
- `Accepted` → `avalon_shares_accepted_total`
- `Rejected` → `avalon_shares_rejected_total`
- `Stale` → `avalon_shares_stale_total`
- `Found Blocks` → `avalon_blocks_found_total`
- `Best Share` → `avalon_best_share`

### Session-level percentages (not per-pool)
These come from `summary`, and represent session-wide ratios:
- `Device Hardware%` → `avalon_device_hw_error_percent`
- `Device Rejected%` → `avalon_device_rejected_percent`
- `Pool Rejected%` → `avalon_pool_rejected_percent`
- `Pool Stale%` → `avalon_pool_stale_percent`

### Work utility (summary)
- `Work Utility` → `avalon_work_utility_summary`

> Distinction: The exporter also emits **per-pool** rejected/stale percentages from `pools` (`Pool Rejected%`, `Pool Stale%`)
> under `avalon_pool_rejected_percent` / `avalon_pool_stale_percent` with pool labels. Those are separate series because they carry
> `pool_index=...` labels.

---

## 5) `stats` command fields (miner-level, STATS=0)

The exporter uses the `STATS=0` segment (miner-level) and parses most values as `KEY[...]`.

### 5.1 Control / state fields

- `WORKMODE[<int>]` — firmware work mode (implementation-defined)  
  Exported as: `avalon_work_mode`

- `Activation[0|1]` — whether hashing is active  
  Exported as: `avalon_activation` (0/1)

- `SoftOFF[0|1]` — software-triggered power-off / disabled state  
  Exported as: `avalon_soft_power_off` (0/1)

- `LcdOnoff[0|1]` — LCD enabled  
  Exported as: `avalon_lcd_on` (0/1)

- `LcdSwitch[0|1]` — LCD switching enabled  
  Exported as: `avalon_lcd_switch` (0/1)

### 5.2 Temperature fields

All are reported in °C.

- `ITemp[<c>]` — inlet/intake temperature  
  Exported as: `avalon_temp_inlet_celsius`  
  *May be `-273` on some Nano 3S firmware; exported as-is for cross-model compatibility.*

- `OTemp[<c>]` — outlet/exhaust temperature  
  Exported as: `avalon_temp_outlet_celsius`

- `TAvg[<c>]` — average ASIC temperature  
  Exported as: `avalon_temp_avg_celsius`

- `TMax[<c>]` — maximum observed ASIC temperature  
  Exported as: `avalon_temp_max_celsius`

- `TarT[<c>]` — target temperature used by the control loop  
  Exported as: `avalon_temp_target_celsius`

> Not parsed by exporter.py (may exist in raw stats): `MTmax`, `MTavg`, and many other diagnostic temps.

### 5.3 ASIC / topology fields

- `TA[<int>]` — **Total ASICs** present (NOT ambient temperature)  
  Exported as: `avalon_total_asics`

### 5.4 Fan / cooling fields

- `Fan1[<rpm>]` — primary fan speed  
  Exported as: `avalon_fan1_rpm`

- `FanR[<percent>]` — fan duty cycle percent  
  Exported as: `avalon_fan_duty_percent`

### 5.5 Hashrate & performance fields

All hashrate values are in **GHS** as reported by the miner.

- `GHSspd[<ghs>]` — instantaneous hashrate  
  Exported as: `avalon_hashrate_ghs`

- `GHSmm[<ghs>]` — moving/medium-window average  
  Exported as: `avalon_hashrate_moving_ghs`

- `GHSavg[<ghs>]` — longer-term average  
  Exported as: `avalon_hashrate_avg_ghs`

- `WU[<float>]` — work utility  
  Exported as: `avalon_work_utility`

- `Freq[<mhz>]` — configured frequency (MHz)  
  Exported as: `avalon_frequency_mhz`

### 5.6 Error & reliability fields

- `HW[<int>]` — hardware error count  
  Exported as: `avalon_hw_errors_total`

- `DH[<percent>]` — hardware error percentage  
  Exported as: `avalon_hw_error_rate_percent`

- `DHspd[<percent>]` — “speed” representation of DH (firmware-defined)  
  Exported as: `avalon_hw_error_rate_speed_percent`

> Not parsed by exporter.py (may exist): `CRC`, `COMCRC`, and other CRC diagnostics.

### 5.7 Miner meta / work characteristics

These appear as `key=value` within the STATS=0 segment:

- `MM Count=<int>` — number of MM modules reported  
  Exported as: `avalon_mm_count`

- `Nonce Mask=<int>` — nonce mask value (used by firmware)  
  Exported as: `avalon_nonce_mask`

### 5.8 Power / PSU fields (`MPO` and `PS[...]`)

#### `MPO[<number>]`
Miner power output / target setting (unit is firmware-defined).
Exported as: `avalon_mpo_target`

#### `PS[ ... ]` raw slots
`PS[...]` is a list of integers. The exporter exports **all slots** as:

- `avalon_ps_slot_0`
- `avalon_ps_slot_1`
- ...
- `avalon_ps_slot_N`

#### Decoded PS slot mapping used by exporter.py

In addition to raw slots, exporter.py decodes specific indices into named metrics:

- `PS[0]` → `avalon_power_err`  
  (PS error/status field, if firmware provides one)

- `PS[2]` → `avalon_power_vout`  
  **vout** = output voltage (units may be scaled/encoded by firmware)

- `PS[3]` → `avalon_power_iout`  
  **iout** = output current (units may be scaled/encoded by firmware)

- `PS[5]` → `avalon_power_vout_cmd`  
  commanded output voltage (firmware-defined)

- `PS[6]` → `avalon_power_pout_wall`  
  wall-side / input-side power (firmware-defined; often used as watts-equivalent)

> Important:
> - The exporter currently treats these as numeric values and does not apply scaling beyond the chip voltage conversion.
> - Different firmware may encode these differently. Use the raw `avalon_ps_slot_*` series when in doubt.

---

## 6) Chip telemetry fields from `stats` (optional)

These fields are parsed from STATS=0 and exported in two ways:
1) **aggregate** metrics (always, if fields exist), and
2) **per-chip** series (only if `EXPORT_CHIP_METRICS=true`).

### 6.1 `PVT_T0[ ... ]` — per-chip temperature list

Raw format: list of integer temperatures (°C).  
Exporter computes aggregates:

- `avalon_chip_temp_min_celsius`
- `avalon_chip_temp_avg_celsius`
- `avalon_chip_temp_max_celsius`

If `EXPORT_CHIP_METRICS=true`, per-chip series:

- `avalon_chip_temp_celsius{chip="0"} ...`

### 6.2 `PVT_V0[ ... ]` — per-chip voltage list

Raw format: list of integers where `303` means **3.03 V**.

Exporter converts each element by dividing by 100.0 and exports aggregates:

- `avalon_chip_voltage_min_volts`
- `avalon_chip_voltage_avg_volts`
- `avalon_chip_voltage_max_volts`

If `EXPORT_CHIP_METRICS=true`, per-chip series:

- `avalon_chip_voltage_volts{chip="0"} ...`

### 6.3 `MW0[ ... ]` — per-chip matching-work / nonce activity list

Raw format: list of integers. This represents **per-chip matching-work / nonce activity** (relative work contribution).

Exporter exports aggregates:

- `avalon_chip_matching_work_min`
- `avalon_chip_matching_work_avg`
- `avalon_chip_matching_work_max`
- `avalon_chip_matching_work_sum`

If `EXPORT_CHIP_METRICS=true`, per-chip series:

- `avalon_chip_matching_work{chip="0"} ...`

### 6.4 Chip count

The exporter computes:

- `avalon_chip_count`

as the maximum length across the three chip lists (`PVT_T0`, `PVT_V0`, `MW0`).

---

## 7) Pool fields from `pools` + `stats` pool records

Pool series include labels:

- `pool_index` — the pool index (0, 1, 2, ...)
- `url` — pool URL (from `pools`)
- `priority` — priority (from `pools`)
- `status` — pool status string (from `pools`)
- `id` — the `ID=POOLx` string (from `stats` pool segments)

### 7.1 From `pools` (POOL= records)

The exporter determines pool availability as:

- `avalon_pool_up = 1` iff (`Status == Alive` AND `Stratum Active == true`)

Other parsed numeric fields (if present) include:

- `avalon_pool_getworks_total` (`Getworks`)
- `avalon_pool_works_total` (`Works`)
- `avalon_pool_discarded_total` (`Discarded`)
- `avalon_pool_stale_total` (`Stale`)
- `avalon_pool_bad_work_total` (`Bad Work`)
- `avalon_pool_get_failures_total` (`Get Failures`)
- `avalon_pool_remote_failures_total` (`Remote Failures`)
- `avalon_pool_shares_accepted_total` (`Accepted`)
- `avalon_pool_shares_rejected_total` (`Rejected`)
- `avalon_pool_diff1_shares_total` (`Diff1 Shares`)
- `avalon_pool_difficulty_accepted` (`Difficulty Accepted`)
- `avalon_pool_difficulty_rejected` (`Difficulty Rejected`)
- `avalon_pool_difficulty_stale` (`Difficulty Stale`)
- `avalon_pool_last_share_difficulty` (`Last Share Difficulty`)
- `avalon_pool_work_difficulty` (`Work Difficulty`)
- `avalon_pool_stratum_difficulty` (`Stratum Difficulty`)
- `avalon_pool_best_share` (`Best Share`)
- `avalon_pool_rejected_percent` (`Pool Rejected%`)
- `avalon_pool_stale_percent` (`Pool Stale%`)
- `avalon_pool_current_block_height` (`Current Block Height`)
- `avalon_pool_current_block_version` (`Current Block Version`)
- `avalon_pool_last_share_time` (`Last Share Time`)

### 7.2 From `stats` pool segments (STATS=1..N, `ID=POOLx`)

Transport and rolling-work fields (if present):

- `avalon_pool_times_sent_total` (`Times Sent`)
- `avalon_pool_times_recv_total` (`Times Recv`)
- `avalon_pool_bytes_sent_total` (`Bytes Sent`)
- `avalon_pool_bytes_recv_total` (`Bytes Recv`)
- `avalon_pool_net_bytes_sent_total` (`Net Bytes Sent`)
- `avalon_pool_net_bytes_recv_total` (`Net Bytes Recv`)
- `avalon_pool_work_diff` (`Work Diff`)
- `avalon_pool_min_diff` (`Min Diff`)
- `avalon_pool_max_diff` (`Max Diff`)
- `avalon_pool_min_diff_count` (`Min Diff Count`)
- `avalon_pool_max_diff_count` (`Max Diff Count`)

Rolling flags / timing:

- `avalon_pool_work_had_roll_time` (`Work Had Roll Time`) — boolean gauge (0/1)
- `avalon_pool_work_can_roll` (`Work Can Roll`) — boolean gauge (0/1)
- `avalon_pool_work_had_expire` (`Work Had Expire`) — boolean gauge (0/1)
- `avalon_pool_work_roll_time_seconds` (`Work Roll Time`) — seconds

---

## 8) Fields intentionally NOT exported by this exporter

- LED configuration fields (`LED[...]`, `LEDUser[...]`, etc.)
- Many firmware diagnostics present in the raw `MM ID0=...` blob that are not parsed in exporter.py
- `estats` (this exporter does not call/parse `estats`)

---

## 9) Quick “what to look at if values seem wrong”

- If power values look odd, graph the raw `avalon_ps_slot_*` series and compare against decoded named fields.
- If `avalon_temp_inlet_celsius` is `-273`, treat it as “unavailable” for that firmware/model; outlet and ASIC temps are usually valid.
- If per-pool series are missing for an idle pool, ensure the pool exists in `pools` output; `stats` pool segments may still be present but sparse.
