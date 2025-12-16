# FIELDS-README.md

This document explains the **raw fields** reported by Avalon A3-series miners via the CGMiner TCP API
and how they are interpreted and exported by `exporter.py`.

It is intended as a reference for:
- Understanding metric semantics
- Debugging unexpected values
- Extending the exporter or dashboards
- Avoiding misinterpretation of low-level telemetry

The exporter primarily consumes data from the following CGMiner commands:

- `version`
- `summary`
- `stats`
- `config`
- `devs`
- `pools`

---

## General Notes

- All values are reported **as-is** unless explicitly noted.
- Some fields may be model-dependent (Nano 3S vs Mini 3).
- Some fields may report placeholder or sentinel values on certain models.
- Chip-level fields are only exported when `EXPORT_CHIP_METRICS=true`.

---

## Miner Identity & Firmware Fields

### `MODEL`
Human-readable miner model name.
Examples:
- `Nano3s`
- `Mini3`

### `HWTYPE`
Hardware platform identifier.
Example:
- `N_MM1v1_X1`

### `SWTYPE`
Software platform identifier used by Canaan firmware.

### `LVER`, `BVER`, `CGBVER`
Firmware version identifiers:
- Loader version
- Board version
- CGMiner build version

### `DNA`
Unique hardware identifier burned into the device.

### `MAC`
Network MAC address.

---

## Time & Uptime Fields

### `Elapsed`
Number of seconds since the miner (or subsystem) started.
Used to derive uptime and stability metrics.

---

## Hashrate & Performance Fields

### `GHSspd`
Instantaneous hashrate in **gigahashes per second**.
Exported as:
- `avalon_hashrate_ghs`

### `GHSavg`
Long-term average hashrate in GHS.
Exported as:
- `avalon_hashrate_avg_ghs`

### `GHSmm`
Moving-average hashrate (medium window).
Exported as:
- `avalon_hashrate_moving_ghs`

### `MGHS`
Alternate average hashrate value reported by some firmware builds.

### `WU`
Work utility.
Represents effective hashing throughput adjusted for difficulty.

---

## Temperature Fields

### `ITemp`
Inlet (intake) temperature in °C.
- May report a placeholder value (e.g. `-273`) on some Nano 3S units.

Exported as:
- `avalon_temp_inlet_celsius`

### `OTemp`
Outlet (exhaust) temperature in °C.
Exported as:
- `avalon_temp_outlet_celsius`

### `TMax`
Maximum observed ASIC temperature.
Exported as:
- `avalon_temp_max_celsius`

### `TAvg`
Average ASIC temperature.
Exported as:
- `avalon_temp_avg_celsius`

### `TarT`
Target temperature used by the miner's thermal control loop.
Exported as:
- `avalon_temp_target_celsius`

### `MTmax`, `MTavg`
Maximum and average temperatures reported across all monitored thermal points.

---

## Fan & Cooling Fields

### `Fan1`
Primary fan speed in RPM.
Exported as:
- `avalon_fan1_rpm`

### `FanR`
Fan duty cycle percentage.
Exported as:
- `avalon_fan_duty_percent`

---

## ASIC & Chip Topology Fields

### `TA`
**Total ASICs** present on the hash board.
This is not a temperature field.

Exported indirectly as a label or reference value.

### `Core`
ASIC core identifier (chip family).

### `BIN`
ASIC binning / quality classification.

---

## Chip-Level Telemetry (Optional)

Only exported when `EXPORT_CHIP_METRICS=true`.

### `PVT_T0`
Per-chip temperature sensor readings.
- Reported as a list of integer °C values.

Used to derive:
- Per-chip min / avg / max temperature metrics.

### `PVT_V0`
Per-chip voltage readings.
- Reported as integers (e.g. `303` = 3.03 V).

Converted and exported as:
- `avalon_chip_voltage_volts`

### `MW0`
Per-chip **matching-work / nonce activity** counters.
- Represents relative per-chip work contribution.
- **Not a power metric**.

Exported as:
- `avalon_chip_matching_work`

---

## Power & Electrical Fields

### `PS[...]`
Raw power-supply telemetry slots.
Slot meanings are firmware-dependent but may include:

- `vout` – Output voltage
- `iout` – Output current
- `pout` – Output power
- `vout_cmd` – Commanded output voltage
- `pout_wall` – Wall-side power draw

When decoded, exported as:
- `avalon_power_vout`
- `avalon_power_iout`
- `avalon_power_pout`
- `avalon_power_vout_cmd`
- `avalon_power_pout_wall`

### `MPO`
Miner power output target.
Exported as:
- `avalon_mpo_target`

---

## Error & Reliability Fields

### `HW`
Total hardware error count.

### `DH`
Hardware error rate percentage.
Exported as:
- `avalon_hw_error_rate_percent`

### `CRC`
CRC error counter.

### `COMCRC`
Communication CRC error counter.

---

## Pool & Network Fields

### `Pool Diff`
Current pool difficulty.

### `Best Share`
Best share difficulty achieved during runtime.
Exported as:
- `avalon_best_share`

### `Times Sent / Recv`
Message counters between miner and pool.

### `Bytes Sent / Recv`
Network byte counters.

Exported as:
- `avalon_pool_bytes_sent_total`
- `avalon_pool_bytes_recv_total`
- `avalon_pool_times_sent_total`
- `avalon_pool_times_recv_total`

---

## Status & Control Fields

### `Activation`
Indicates whether the miner is actively hashing.

### `SoftOFF`
Indicates a software-triggered shutdown state.

### `WORKMODE`, `WORKLEVEL`
Internal firmware work scheduling parameters.

---

## Final Notes

- Field availability and accuracy can vary by firmware revision.
- Placeholder values are exported intentionally to preserve compatibility.
- This document reflects observed behavior on Avalon Nano 3S and Mini 3 miners.
- Contributions clarifying additional fields or firmware variants are welcome.
