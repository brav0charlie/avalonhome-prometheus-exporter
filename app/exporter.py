#!/usr/bin/env python3
import os
import socket
import time
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ======================
# Config (env overridable, NO legacy support)
# ======================


# Back-compat: accept old AVALON3_* env vars too
AVALON_IPS_ENV = (os.getenv("AVALON_IPS", "") or "").strip()
SINGLE_IP_ENV = (os.getenv("AVALON_IP", "") or "").strip()
MINER_PORT = int(os.getenv("AVALON_PORT", "4028"))
UPDATE_INTERVAL = float(os.getenv("UPDATE_INTERVAL", "10"))  # seconds
EXPORTER_PORT = int(os.getenv("EXPORTER_PORT", "9100"))

# Optional: export per-chip metrics (can be a LOT of series)
EXPORT_CHIP_METRICS = os.getenv("EXPORT_CHIP_METRICS", "0").lower() in ("1", "true", "yes", "on")

# Optional: TCP timeout to miner API
MINER_TIMEOUT = float(os.getenv("MINER_TIMEOUT", "5.0"))

# One-shot combined command (single TCP request)
COMBINED_CMD = "version+summary+stats+config+devs+devdetails+pools"

# Build target list
TARGETS: list[dict[str, object]] = []  # {"ip": str, "port": int}

if AVALON_IPS_ENV:
    for host in AVALON_IPS_ENV.split(","):
        host = host.strip()
        if host:
            TARGETS.append({"ip": host, "port": MINER_PORT})
elif SINGLE_IP_ENV:
    TARGETS.append({"ip": SINGLE_IP_ENV, "port": MINER_PORT})
else:
    raise SystemExit(
        "You must set AVALON_IPS (comma-separated) or AVALON_IP "
        "to tell the exporter which miner(s) to scrape."
    )

# ======================
# Shared state
# ======================

# latest_metrics: { ip -> { metric_name -> value } }
latest_metrics: dict[str, dict[str, float]] = {}
# latest_pools: { ip -> [ {labels: {...}, metrics: {...}} ] }
latest_pools: dict[str, list[dict[str, object]]] = {}
# latest_chips: { ip -> [ {labels: {...}, metrics: {...}} ] } (only if EXPORT_CHIP_METRICS)
latest_chips: dict[str, list[dict[str, object]]] = {}
# version_info: { ip -> {key: value} }
version_info: dict[str, dict[str, str]] = {}
# last_error: { ip -> error str or None }
last_error: dict[str, str | None] = {}
# last_update_ts: { ip -> timestamp float of last successful scrape }
last_update_ts: dict[str, float] = {}
# miner_up: { ip -> 0.0 or 1.0 }
miner_up: dict[str, float] = {}
# per-miner scrape error counters
scrape_errors_total: dict[str, float] = {}
# per-miner status change counters
status_changes_total: dict[str, float] = {}
status_ups_total: dict[str, float] = {}
status_downs_total: dict[str, float] = {}

# Exporter health (poller heartbeat)
poller_last_heartbeat = 0.0
metrics_lock = threading.Lock()

# ======================
# Low-level miner communication
# ======================

def query_miner(host: str, port: int, cmd: str, timeout: float = MINER_TIMEOUT) -> str:
    """
    Connect to the miner API over TCP and send a command string.
    Equivalent to: echo -n "cmd" | socat stdio tcp:host:port,shut-none
    """
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(cmd.encode("ascii"))  # no newline
        s.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        while True:
            data = s.recv(4096)
            if not data:
                break
            chunks.append(data)
        return b"".join(chunks).decode("ascii", errors="replace")

# ======================
# Parsing helpers
# ======================

def find_bracket(key: str, text: str, default: str = "N/A") -> str:
    """Find KEY[...] style values in a blob, e.g. WORKMODE[2] -> '2'."""
    m = re.search(rf"{re.escape(key)}\[([^\]]*)\]", text)
    if m:
        return m.group(1).strip()
    return default

def find_kv(key: str, text: str, default: str = "N/A") -> str:
    """Find key=value style fields, stopping at comma or pipe."""
    m = re.search(rf"{re.escape(key)}=([^,|]+)", text)
    if m:
        return m.group(1).strip()
    return default

def parse_float(value: str | None):
    """Parse a float; strip % if present. Returns None on failure."""
    if value is None:
        return None
    s = str(value).strip().replace("%", "")
    if s == "" or s.upper() == "N/A":
        return None
    try:
        return float(s)
    except ValueError:
        return None

def parse_int(value: str | None):
    """Parse an int. Returns None on failure."""
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.upper() == "N/A":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None

def workmode_numeric(mode: str):
    """Return numeric work mode 0/1/2, or None."""
    return parse_int(mode)

def on_off_numeric(raw_val: str):
    """Map 0/1 to 0.0/1.0 (gauge)."""
    return 1.0 if str(raw_val) == "1" else 0.0

def bool_numeric(raw_val: str | None):
    """Convert true/false, Y/N, Alive/Dead etc into 0.0/1.0."""
    if raw_val is None:
        return 0.0
    s = str(raw_val).strip().lower()
    if s in ("true", "y", "yes", "1", "alive", "up"):
        return 1.0
    return 0.0

def parse_csv_kv(segment: str) -> dict[str, str]:
    """Parse a CSV segment of key=value pairs into a dict. Handles keys with spaces."""
    result: dict[str, str] = {}
    for token in segment.split(","):
        token = token.strip()
        if "=" in token:
            key, val = token.split("=", 1)
            result[key.strip()] = val.strip()
    return result

def parse_int_list(s: str | None) -> list[int]:
    """Parse a bracket list like: ' 83 90 94' into [83, 90, 94]. Accepts negative values too."""
    if s is None:
        return []
    nums = re.findall(r"-?\d+", str(s))
    out: list[int] = []
    for n in nums:
        try:
            out.append(int(n))
        except ValueError:
            pass
    return out

def agg_stats(values: list[float] | list[int]):
    """Return (min, avg, max, sum) for a numeric list. avg is float. Returns (None, None, None, None) if empty."""
    if not values:
        return (None, None, None, None)
    mn = min(values)
    mx = max(values)
    sm = sum(values)
    av = sm / float(len(values))
    return (mn, av, mx, sm)

def extract_stats_segments(stats_section: str) -> list[str]:
    """Split a stats section into individual STATS=... segments."""
    segments: list[str] = []
    for seg in stats_section.split("|"):
        seg = seg.strip()
        if seg.startswith("STATS="):
            segments.append(seg)
    return segments

def get_stats0_segment(stats_section: str) -> str | None:
    """Return STATS=0 segment (miner-level). None if not found."""
    for seg in extract_stats_segments(stats_section):
        if seg.startswith("STATS=0"):
            return seg
    return None

def pool_index_from_id(pool_id: str, stats_num: str = "") -> str:
    """Given ID like 'POOL0' -> '0'. Fallback: if stats_num is digit-like, treat pool index as stats_num - 1."""
    if pool_id:
        m = re.search(r"POOL(\d+)", pool_id.strip(), re.IGNORECASE)
        if m:
            return m.group(1)
    try:
        n = int(stats_num)
        if n >= 1:
            return str(n - 1)
    except Exception:
        pass
    return ""

def parse_ps_list(ps_raw: str) -> list[int]:
    """Parse PS[...] list (space-separated ints) into list of ints."""
    if ps_raw is None or ps_raw.upper() == "N/A":
        return []
    return parse_int_list(ps_raw)

def split_combined_response(raw: str) -> dict[str, str]:
    """
    Turn:
      CMD=version|...|CMD=summary|...|CMD=stats|...|
    into:
      {"version": "CMD=version|...|", "summary": "...", ...}
    """
    out: dict[str, str] = {}
    if not raw:
        return out

    # Split on '|CMD=' boundaries, but keep the 'CMD=' marker.
    parts = raw.split("|CMD=")
    first = parts[0]
    if first.startswith("CMD="):
        parts = [first] + ["CMD=" + p for p in parts[1:]]
    else:
        parts = ["CMD=" + first] + ["CMD=" + p for p in parts[1:]]

    for p in parts:
        p = p.strip()
        if not p.startswith("CMD="):
            continue
        cmd_name = find_kv("CMD", p, default="").strip().lower()
        if cmd_name:
            out[cmd_name] = p
    return out

def extract_version_info_from_section(section: str) -> dict[str, str]:
    """Extract the VERSION,... kv set from a combined response 'version' section."""
    segment = None
    for seg in section.split("|"):
        seg = seg.strip()
        if seg.startswith("VERSION"):
            segment = seg
            break
    if not segment:
        return {}

    if segment.startswith("VERSION,"):
        _, _, rest = segment.partition(",")
        kv = parse_csv_kv(rest)
    else:
        kv = parse_csv_kv(segment)

    model = kv.get("MODEL", "")
    prod = kv.get("PROD", "")
    firmware = kv.get("LVERSION", "") or kv.get("CGVERSION", "")
    cgminer_ver = kv.get("CGMiner", "")
    api_ver = kv.get("API", "")
    hwtype = kv.get("HWTYPE", "")
    swtype = kv.get("SWTYPE", "")
    dna = kv.get("DNA", "")
    mac = kv.get("MAC", "")

    return {
        "model": model,
        "prod": prod,
        "firmware": firmware,
        "cgminer": cgminer_ver,
        "api": api_ver,
        "hwtype": hwtype,
        "swtype": swtype,
        "dna": dna,
        "mac": mac,
    }

# ======================
# Metric collection
# ======================

def collect_for(ip: str, port: int):
    """
    Single TCP scrape using COMBINED_CMD, then parse:
      - miner-level metrics (stats + summary)
      - pools (pools + stats pool records)
      - chip aggregates (stats)
      - version info (version)
    """
    raw = query_miner(ip, port, COMBINED_CMD)
    sections = split_combined_response(raw)

    version_section = sections.get("version", "")
    summary_section = sections.get("summary", "")
    stats_section = sections.get("stats", "")
    pools_section = sections.get("pools", "")

    metrics: dict[str, float] = {}
    pools: list[dict[str, object]] = []
    chips: list[dict[str, object]] = []

    stats0 = get_stats0_segment(stats_section) or ""

    # -------- Miner-level metrics --------

    # Uptime: prefer summary Elapsed, fallback stats0 Elapsed
    elapsed = find_kv("Elapsed", summary_section, default="0")
    if elapsed == "0":
        elapsed = find_kv("Elapsed", stats0, default="0")
    metrics["avalon_uptime_seconds"] = parse_float(elapsed) or 0.0

    # Work mode & binary flags
    wm = workmode_numeric(find_bracket("WORKMODE", stats0, default=""))
    if wm is not None:
        metrics["avalon_work_mode"] = float(wm)

    metrics["avalon_activation"] = on_off_numeric(find_bracket("Activation", stats0, default="0"))
    metrics["avalon_soft_power_off"] = on_off_numeric(find_bracket("SoftOFF", stats0, default="0"))
    metrics["avalon_lcd_on"] = on_off_numeric(find_bracket("LcdOnoff", stats0, default="0"))
    metrics["avalon_lcd_switch"] = on_off_numeric(find_bracket("LcdSwitch", stats0, default="0"))

    # Temps (report ITemp as-is, even if -273)
    for key, val in [
        ("avalon_temp_inlet_celsius", find_bracket("ITemp", stats0, default="N/A")),
        ("avalon_temp_outlet_celsius", find_bracket("OTemp", stats0, default="N/A")),
        ("avalon_temp_avg_celsius", find_bracket("TAvg", stats0, default="N/A")),
        ("avalon_temp_max_celsius", find_bracket("TMax", stats0, default="N/A")),
        ("avalon_temp_target_celsius", find_bracket("TarT", stats0, default="N/A")),
    ]:
        f = parse_float(val)
        if f is not None:
            metrics[key] = f

    # TA = Total ASICs (NOT ambient temperature)
    total_asics = parse_int(find_bracket("TA", stats0, default="N/A"))
    if total_asics is not None:
        metrics["avalon_total_asics"] = float(total_asics)

    # Fans
    f_fan1 = parse_float(find_bracket("Fan1", stats0, default="N/A"))
    if f_fan1 is not None:
        metrics["avalon_fan1_rpm"] = f_fan1
    f_fanr = parse_float(find_bracket("FanR", stats0, default="N/A"))
    if f_fanr is not None:
        metrics["avalon_fan_duty_percent"] = f_fanr

    # Hashrate & WU
    for key, val in [
        ("avalon_hashrate_ghs", find_bracket("GHSspd", stats0, default="N/A")),
        ("avalon_hashrate_moving_ghs", find_bracket("GHSmm", stats0, default="N/A")),
        ("avalon_hashrate_avg_ghs", find_bracket("GHSavg", stats0, default="N/A")),
        ("avalon_work_utility", find_bracket("WU", stats0, default="N/A")),
        ("avalon_frequency_mhz", find_bracket("Freq", stats0, default="N/A")),
    ]:
        f = parse_float(val)
        if f is not None:
            metrics[key] = f

    f_dh = parse_float(find_bracket("DH", stats0, default="N/A"))
    if f_dh is not None:
        metrics["avalon_hw_error_rate_percent"] = f_dh

    f_dhspd = parse_float(find_bracket("DHspd", stats0, default="N/A"))
    if f_dhspd is not None:
        metrics["avalon_hw_error_rate_speed_percent"] = f_dhspd

    i_hw = parse_int(find_bracket("HW", stats0, default="N/A"))
    if i_hw is not None:
        metrics["avalon_hw_errors_total"] = float(i_hw)

    # MPO (target power consumption) - numeric, unit as reported by firmware
    mpo = parse_float(find_bracket("MPO", stats0, default="N/A"))
    if mpo is not None:
        metrics["avalon_mpo_target"] = mpo

    # MM Count / Nonce Mask (if present)
    mm_count = parse_int(find_kv("MM Count", stats0, default="N/A"))
    if mm_count is not None:
        metrics["avalon_mm_count"] = float(mm_count)

    nonce_mask = parse_int(find_kv("Nonce Mask", stats0, default="N/A"))
    if nonce_mask is not None:
        metrics["avalon_nonce_mask"] = float(nonce_mask)

    # Power PS[...] (export named fields + raw slots)
    ps_vals = parse_ps_list(find_bracket("PS", stats0, default="N/A"))
    for idx, v in enumerate(ps_vals):
        metrics[f"avalon_ps_slot_{idx}"] = float(v)

    # Named slots (Nano3s driver-avalon.c semantics)
    # index: 0=err, 2=vout, 3=iout, 5=voutcmd, 6=poutwall
    if len(ps_vals) > 0:
        metrics["avalon_power_err"] = float(ps_vals[0])
    if len(ps_vals) > 2:
        metrics["avalon_power_vout"] = float(ps_vals[2])
    if len(ps_vals) > 3:
        metrics["avalon_power_iout"] = float(ps_vals[3])
    if len(ps_vals) > 5:
        metrics["avalon_power_vout_cmd"] = float(ps_vals[5])
    if len(ps_vals) > 6:
        metrics["avalon_power_pout_wall"] = float(ps_vals[6])

    # Shares / pool stats from summary
    for key, val in [
        ("avalon_shares_accepted_total", find_kv("Accepted", summary_section, default="N/A")),
        ("avalon_shares_rejected_total", find_kv("Rejected", summary_section, default="N/A")),
        ("avalon_shares_stale_total", find_kv("Stale", summary_section, default="N/A")),
        ("avalon_blocks_found_total", find_kv("Found Blocks", summary_section, default="N/A")),
        ("avalon_best_share", find_kv("Best Share", summary_section, default="N/A")),
    ]:
        v = parse_float(val)
        if v is not None:
            metrics[key] = v

    for key, val in [
        ("avalon_device_hw_error_percent", find_kv("Device Hardware%", summary_section, default="N/A")),
        ("avalon_device_rejected_percent", find_kv("Device Rejected%", summary_section, default="N/A")),
        ("avalon_pool_rejected_percent", find_kv("Pool Rejected%", summary_section, default="N/A")),
        ("avalon_pool_stale_percent", find_kv("Pool Stale%", summary_section, default="N/A")),
        ("avalon_work_utility_summary", find_kv("Work Utility", summary_section, default="N/A")),
    ]:
        f = parse_float(val)
        if f is not None:
            metrics[key] = f

    # -------- Chip array aggregates --------
    # Chip temps (PVT_T0), voltages (PVT_V0), chip matching-work telemetry (MW0)
    chip_t_raw = find_bracket("PVT_T0", stats0, default="N/A")
    chip_v_raw = find_bracket("PVT_V0", stats0, default="N/A")
    chip_mw_raw = find_bracket("MW0", stats0, default="N/A")

    chip_t = parse_int_list(chip_t_raw) if chip_t_raw != "N/A" else []
    chip_v_ints = parse_int_list(chip_v_raw) if chip_v_raw != "N/A" else []
    chip_mw = parse_int_list(chip_mw_raw) if chip_mw_raw != "N/A" else []

    chip_count = max(len(chip_t), len(chip_v_ints), len(chip_mw))
    if chip_count > 0:
        metrics["avalon_chip_count"] = float(chip_count)

    # temp aggregates
    t_min, t_avg_f, t_max, _ = agg_stats(chip_t)
    if t_min is not None:
        metrics["avalon_chip_temp_min_celsius"] = float(t_min)
        metrics["avalon_chip_temp_avg_celsius"] = float(t_avg_f)
        metrics["avalon_chip_temp_max_celsius"] = float(t_max)

    # voltage aggregates (raw int like 303 -> 3.03V)
    chip_v = [v / 100.0 for v in chip_v_ints] if chip_v_ints else []
    v_min, v_avg_f, v_max, _ = agg_stats(chip_v)
    if v_min is not None:
        metrics["avalon_chip_voltage_min_volts"] = float(v_min)
        metrics["avalon_chip_voltage_avg_volts"] = float(v_avg_f)
        metrics["avalon_chip_voltage_max_volts"] = float(v_max)

    # MW0 aggregates (matching-work telemetry)
    mw_min, mw_avg_f, mw_max, mw_sum = agg_stats(chip_mw)
    if mw_min is not None:
        metrics["avalon_chip_matching_work_min"] = float(mw_min)
        metrics["avalon_chip_matching_work_avg"] = float(mw_avg_f)
        metrics["avalon_chip_matching_work_max"] = float(mw_max)
        metrics["avalon_chip_matching_work_sum"] = float(mw_sum)

    # Optional per-chip metrics
    if EXPORT_CHIP_METRICS:
        for idx, val in enumerate(chip_t):
            chips.append({"labels": {"chip": str(idx)}, "metrics": {"avalon_chip_temp_celsius": float(val)}})
        for idx, val in enumerate(chip_v_ints):
            chips.append({"labels": {"chip": str(idx)}, "metrics": {"avalon_chip_voltage_volts": float(val) / 100.0}})
        for idx, val in enumerate(chip_mw):
            chips.append({"labels": {"chip": str(idx)}, "metrics": {"avalon_chip_matching_work": float(val)}})

    # -------- Per-pool metrics --------
    pool_map: dict[str, dict[str, object]] = {}

    # pools() gives URL/status/priority + share/difficulty stats
    for segment in pools_section.split("|"):
        segment = segment.strip()
        if not segment.startswith("POOL="):
            continue
        pool_kv = parse_csv_kv(segment)
        pool_index = pool_kv.get("POOL", "")
        url = pool_kv.get("URL", "")
        priority = pool_kv.get("Priority", "")
        status = pool_kv.get("Status", "")
        stratum_active = pool_kv.get("Stratum Active", "")
        status_ok = status.strip().lower() == "alive"
        stratum_ok = stratum_active.strip().lower() == "true"
        pool_up = 1.0 if (status_ok and stratum_ok) else 0.0

        def pf(key: str):
            return parse_float(pool_kv.get(key, "N/A"))

        pool_metrics: dict[str, float] = {"avalon_pool_up": pool_up}
        for name, key in [
            ("avalon_pool_getworks_total", "Getworks"),
            ("avalon_pool_works_total", "Works"),
            ("avalon_pool_discarded_total", "Discarded"),
            ("avalon_pool_stale_total", "Stale"),
            ("avalon_pool_bad_work_total", "Bad Work"),
            ("avalon_pool_get_failures_total", "Get Failures"),
            ("avalon_pool_remote_failures_total", "Remote Failures"),
            ("avalon_pool_shares_accepted_total", "Accepted"),
            ("avalon_pool_shares_rejected_total", "Rejected"),
            ("avalon_pool_diff1_shares_total", "Diff1 Shares"),
            ("avalon_pool_difficulty_accepted", "Difficulty Accepted"),
            ("avalon_pool_difficulty_rejected", "Difficulty Rejected"),
            ("avalon_pool_difficulty_stale", "Difficulty Stale"),
            ("avalon_pool_last_share_difficulty", "Last Share Difficulty"),
            ("avalon_pool_work_difficulty", "Work Difficulty"),
            ("avalon_pool_stratum_difficulty", "Stratum Difficulty"),
            ("avalon_pool_best_share", "Best Share"),
            ("avalon_pool_rejected_percent", "Pool Rejected%"),
            ("avalon_pool_stale_percent", "Pool Stale%"),
            ("avalon_pool_current_block_height", "Current Block Height"),
            ("avalon_pool_current_block_version", "Current Block Version"),
            ("avalon_pool_last_share_time", "Last Share Time"),
        ]:
            val = pf(key)
            if val is not None:
                pool_metrics[name] = val

        pool_labels = {
            "pool_index": pool_index,
            "url": url,
            "priority": priority,
            "status": status,
        }
        pool_map[pool_index] = {"labels": pool_labels, "metrics": pool_metrics}

    # stats() includes STATS=1..N pool transport metrics (Times Sent/Recv, bytes, diffs, etc.)
    for seg in extract_stats_segments(stats_section):
        kv = parse_csv_kv(seg)
        stats_num = kv.get("STATS", "")
        pid = kv.get("ID", "")
        if not pid or not str(pid).upper().startswith("POOL"):
            continue

        pool_index = pool_index_from_id(pid, stats_num)
        if pool_index not in pool_map:
            pool_map[pool_index] = {
                "labels": {"pool_index": pool_index, "url": "", "priority": "", "status": ""},
                "metrics": {"avalon_pool_up": 0.0},
            }

        pool_map[pool_index]["labels"]["id"] = pid

        def pf_k(key: str, default: str = "N/A"):
            return parse_float(kv.get(key, default))

        def pb_k(key: str, default: str = "false"):
            return bool_numeric(kv.get(key, default))

        stats_pool_metrics = {
            "avalon_pool_times_sent_total": pf_k("Times Sent"),
            "avalon_pool_times_recv_total": pf_k("Times Recv"),
            "avalon_pool_bytes_sent_total": pf_k("Bytes Sent"),
            "avalon_pool_bytes_recv_total": pf_k("Bytes Recv"),
            "avalon_pool_net_bytes_sent_total": pf_k("Net Bytes Sent"),
            "avalon_pool_net_bytes_recv_total": pf_k("Net Bytes Recv"),
            "avalon_pool_work_diff": pf_k("Work Diff"),
            "avalon_pool_min_diff": pf_k("Min Diff"),
            "avalon_pool_max_diff": pf_k("Max Diff"),
            "avalon_pool_min_diff_count": pf_k("Min Diff Count"),
            "avalon_pool_max_diff_count": pf_k("Max Diff Count"),
            "avalon_pool_work_had_roll_time": pb_k("Work Had Roll Time"),
            "avalon_pool_work_can_roll": pb_k("Work Can Roll"),
            "avalon_pool_work_had_expire": pb_k("Work Had Expire"),
            "avalon_pool_work_roll_time_seconds": pf_k("Work Roll Time"),
        }

        for kname, v in stats_pool_metrics.items():
            if v is not None:
                pool_map[pool_index]["metrics"][kname] = v

    for idx in sorted(pool_map.keys(), key=lambda x: int(x) if str(x).isdigit() else 9999):
        pools.append(pool_map[idx])

    # Version info
    vinfo = extract_version_info_from_section(version_section)

    return metrics, pools, chips, vinfo

def poller_loop():
    """Background loop that polls all miners every UPDATE_INTERVAL seconds."""
    global poller_last_heartbeat
    while True:
        poller_last_heartbeat = time.time()
        for tinfo in TARGETS:
            ip = str(tinfo["ip"])
            port = int(tinfo["port"])
            try:
                m, pools, chips, vinfo = collect_for(ip, port)
                now = time.time()
                with metrics_lock:
                    latest_metrics[ip] = m
                    latest_pools[ip] = pools
                    latest_chips[ip] = chips
                    last_error[ip] = None
                    last_update_ts[ip] = now

                    prev_up = miner_up.get(ip)
                    miner_up[ip] = 1.0
                    if prev_up is not None and prev_up != 1.0:
                        status_changes_total[ip] = status_changes_total.get(ip, 0.0) + 1.0
                        status_ups_total[ip] = status_ups_total.get(ip, 0.0) + 1.0

                    if vinfo:
                        version_info[ip] = vinfo
            except Exception as e:
                with metrics_lock:
                    last_error[ip] = str(e)
                    prev_up = miner_up.get(ip)
                    miner_up[ip] = 0.0
                    scrape_errors_total[ip] = scrape_errors_total.get(ip, 0.0) + 1.0
                    if prev_up is not None and prev_up != 0.0:
                        status_changes_total[ip] = status_changes_total.get(ip, 0.0) + 1.0
                        status_downs_total[ip] = status_downs_total.get(ip, 0.0) + 1.0

        time.sleep(UPDATE_INTERVAL)

# ======================
# HTTP Handler
# ======================

class AvalonHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.handle_metrics()
        elif self.path == "/health" or self.path == "/":
            self.handle_health()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found\n")

    def log_message(self, fmt, *args):
        return

    def handle_health(self):
        """
        Exporter health means:
          - HTTP server is up
          - poller thread is still ticking
        NOT "all miners are up"
        """
        now = time.time()
        hb = poller_last_heartbeat
        unhealthy = (hb == 0.0) or ((now - hb) > max(30.0, UPDATE_INTERVAL * 3.0))
        self.send_response(503 if unhealthy else 200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        if unhealthy:
            self.wfile.write(f"UNHEALTHY: poller heartbeat stale (last={hb}, now={now})\n".encode("utf-8"))
        else:
            self.wfile.write(b"OK\n")

    def handle_metrics(self):
        now = time.time()
        with metrics_lock:
            metrics_snapshot = {ip: dict(m) for ip, m in latest_metrics.items()}
            pools_snapshot = {ip: list(p) for ip, p in latest_pools.items()}
            chips_snapshot = {ip: list(c) for ip, c in latest_chips.items()}
            errors_snapshot = dict(last_error)
            updates_snapshot = dict(last_update_ts)
            miner_up_snapshot = dict(miner_up)
            scrape_errors_snapshot = dict(scrape_errors_total)
            status_changes_snapshot = dict(status_changes_total)
            status_ups_snapshot = dict(status_ups_total)
            status_downs_snapshot = dict(status_downs_total)
            version_info_snapshot = dict(version_info)

        lines: list[str] = []

        # Core up/down & scrape metrics
        lines.append("# HELP avalon_up Was the last scrape of the Avalon miner successful.")
        lines.append("# TYPE avalon_up gauge")
        lines.append("# HELP avalon_last_scrape_timestamp_seconds Unix time of last successful scrape.")
        lines.append("# TYPE avalon_last_scrape_timestamp_seconds gauge")
        lines.append("# HELP avalon_down_duration_seconds How long the miner has been down (seconds).")
        lines.append("# TYPE avalon_down_duration_seconds gauge")
        lines.append("# HELP avalon_scrape_errors_total Total number of scrape errors for this miner.")
        lines.append("# TYPE avalon_scrape_errors_total counter")
        lines.append("# HELP avalon_status_changes_total Total number of up/down status changes for this miner.")
        lines.append("# TYPE avalon_status_changes_total counter")
        lines.append("# HELP avalon_status_ups_total Total number of transitions to UP for this miner.")
        lines.append("# TYPE avalon_status_ups_total counter")
        lines.append("# HELP avalon_status_downs_total Total number of transitions to DOWN for this miner.")
        lines.append("# TYPE avalon_status_downs_total counter")

        for tinfo in TARGETS:
            ip = str(tinfo["ip"])
            updated = updates_snapshot.get(ip, 0.0)
            err = errors_snapshot.get(ip)
            up_val = miner_up_snapshot.get(ip, 0.0)
            if ip not in miner_up_snapshot:
                up_val = 1.0 if (err is None and (now - updated) < UPDATE_INTERVAL * 3) else 0.0

            if up_val == 0.0 and updated > 0.0:
                down_for = now - updated
            elif up_val == 0.0 and updated == 0.0:
                down_for = 0.0
            else:
                down_for = 0.0

            errors_count = scrape_errors_snapshot.get(ip, 0.0)
            status_changes = status_changes_snapshot.get(ip, 0.0)
            status_ups = status_ups_snapshot.get(ip, 0.0)
            status_downs = status_downs_snapshot.get(ip, 0.0)

            lines.append(f'avalon_up{{ip="{ip}"}} {up_val}')
            lines.append(f'avalon_last_scrape_timestamp_seconds{{ip="{ip}"}} {updated}')
            lines.append(f'avalon_down_duration_seconds{{ip="{ip}"}} {down_for}')
            lines.append(f'avalon_scrape_errors_total{{ip="{ip}"}} {errors_count}')
            lines.append(f'avalon_status_changes_total{{ip="{ip}"}} {status_changes}')
            lines.append(f'avalon_status_ups_total{{ip="{ip}"}} {status_ups}')
            lines.append(f'avalon_status_downs_total{{ip="{ip}"}} {status_downs}')

        # Miner-level metrics
        for ip, metrics_for_ip in sorted(metrics_snapshot.items()):
            for name, val in sorted(metrics_for_ip.items()):
                lines.append(f'{name}{{ip="{ip}"}} {val}')

        # Per-chip metrics (optional)
        if EXPORT_CHIP_METRICS:
            lines.append("# HELP avalon_chip_temp_celsius Per-chip temperature derived from PVT_T0 (if present).")
            lines.append("# TYPE avalon_chip_temp_celsius gauge")
            lines.append("# HELP avalon_chip_voltage_volts Per-chip voltage derived from PVT_V0 (if present).")
            lines.append("# TYPE avalon_chip_voltage_volts gauge")
            lines.append("# HELP avalon_chip_matching_work Per-chip matching-work telemetry derived from MW0 (if present).")
            lines.append("# TYPE avalon_chip_matching_work gauge")

            for ip, chips_for_ip in sorted(chips_snapshot.items()):
                for chip in chips_for_ip:
                    labels = chip.get("labels", {})
                    label_parts = [f'ip="{ip}"']
                    for k, v in labels.items():
                        v_str = str(v).replace('"', "'")
                        label_parts.append(f'{k}="{v_str}"')
                    label_str = ",".join(label_parts)
                    for name, val in chip.get("metrics", {}).items():
                        lines.append(f"{name}{{{label_str}}} {val}")

        # Pool-level metrics
        for ip, pools_for_ip in sorted(pools_snapshot.items()):
            for pool in pools_for_ip:
                labels = pool.get("labels", {})
                label_parts = [f'ip="{ip}"']
                for k, v in labels.items():
                    v_str = str(v).replace('"', "'")
                    label_parts.append(f'{k}="{v_str}"')
                label_str = ",".join(label_parts)
                for name, val in sorted(pool.get("metrics", {}).items()):
                    lines.append(f"{name}{{{label_str}}} {val}")

        # Static info metric
        lines.append("# HELP avalon_info Static info about the Avalon miner (model, firmware, etc).")
        lines.append("# TYPE avalon_info gauge")
        for ip, vinfo in sorted(version_info_snapshot.items()):
            label_parts = [f'ip="{ip}"']
            for k, v in vinfo.items():
                v_str = str(v).replace('"', "'")
                label_parts.append(f'{k}="{v_str}"')
            label_str = ",".join(label_parts)
            lines.append(f'avalon_info{{{label_str}}} 1')

        body = "\n".join(lines) + "\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

# ======================
# Main
# ======================

def main():
    t = threading.Thread(target=poller_loop, daemon=True)
    t.start()
    server = HTTPServer(("0.0.0.0", EXPORTER_PORT), AvalonHandler)
    print(
        f"Avalon exporter listening on 0.0.0.0:{EXPORTER_PORT}, "
        f"polling {len(TARGETS)} miner(s) every {UPDATE_INTERVAL}s "
        f"(combined cmd: {COMBINED_CMD}; export_chip_metrics={EXPORT_CHIP_METRICS})"
    )
    for tinfo in TARGETS:
        print(f" - {tinfo['ip']}:{tinfo['port']}")
    server.serve_forever()

if __name__ == "__main__":
    main()