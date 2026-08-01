import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import exporter  # noqa: E402


SUMMARY_1047 = (
    "CMD=summary|SUMMARY,Elapsed=3600,MHS av=30000000.00,"
    "MHS 30s=33000000.00,MHS 1m=32000000.00,MHS 5m=31000000.00,"
    "MHS 15m=30500000.00,Found Blocks=0,Accepted=42,Rejected=1,"
    "Stale=0,Hardware Errors=7,Work Utility=450.5,Device Hardware%=0.01,"
    "Device Rejected%=0.02,Pool Rejected%=0.03,Pool Stale%=0.00|"
)

STATS0_1047 = (
    "STATS=0,ID=AV1047,Elapsed=3600,MM Count=2,"
    "MM ID0[Ver[synthetic],DNA[REDACTED],SYSTEMSTATU[Work: In Work, Hash Board: 2],"
    "Temp[66],TMax[82],TAvg[70],Fan1[5600],Fan2[5700],FanR[88%],"
    "GHSmm[33300.5],GHSavg[32100.25],WU[450.5],Freq[625],HW[7],DH[0.01%],"
    "MPO[2220],PVT_T0[60 61 62],PVT_T1[63 64 65],"
    "PVT_V0[303 304 305],PVT_V1[306 307 308],MW0[1 2 3],MW1[4 5 6]]|"
)

VERSION_1047 = (
    "CMD=version|VERSION,CGMiner=4.11.1,API=3.7,MODEL=1047,"
    "PROD=AvalonMiner 1047,LVERSION=synthetic,DNA=REDACTED,MAC=REDACTED|"
)


class AvalonMiner1047ParsingTest(unittest.TestCase):
    def test_system_working_handles_official_avalon_states(self):
        cases = {
            "Work: In Work, Hash Board: 2": 1.0,
            "Work: In Idle, Hash Board: 2": 0.0,
            "Work: In Init, Hash Board: 2": 0.0,
            "Work: In Fault, Hash Board: 2": 0.0,
        }

        for status, want in cases.items():
            with self.subTest(status=status):
                self.assertEqual(exporter.parse_system_working(status), want)

    def test_system_working_preserves_none_for_unknown_status(self):
        self.assertIsNone(exporter.parse_system_working("Work: In Mystery, Hash Board: 2"))

    def test_miner_metrics_parse_1047_summary_and_stats_fields(self):
        metrics = exporter._parse_miner_metrics(STATS0_1047, SUMMARY_1047)

        self.assertEqual(metrics["avalon_temp_current_celsius"], 66.0)
        self.assertEqual(metrics["avalon_temp_max_celsius"], 82.0)
        self.assertEqual(metrics["avalon_temp_avg_celsius"], 70.0)
        self.assertEqual(metrics["avalon_fan1_rpm"], 5600.0)
        self.assertEqual(metrics["avalon_fan2_rpm"], 5700.0)
        self.assertEqual(metrics["avalon_fan_duty_percent"], 88.0)
        self.assertEqual(metrics["avalon_hash_boards"], 2.0)
        self.assertEqual(metrics["avalon_system_working"], 1.0)

        self.assertEqual(metrics["avalon_hashrate_ghs"], 33000.0)
        self.assertEqual(metrics["avalon_hashrate_1m_ghs"], 32000.0)
        self.assertEqual(metrics["avalon_hashrate_5m_ghs"], 31000.0)
        self.assertEqual(metrics["avalon_hashrate_15m_ghs"], 30500.0)
        self.assertEqual(metrics["avalon_hashrate_moving_ghs"], 33300.5)
        self.assertEqual(metrics["avalon_hashrate_avg_ghs"], 32100.25)

    def test_chip_aggregates_include_second_hash_board_arrays(self):
        metrics, chips = exporter._parse_chip_metrics(STATS0_1047)

        self.assertEqual(chips, [])
        self.assertEqual(metrics["avalon_chip_count"], 6.0)
        self.assertEqual(metrics["avalon_chip_temp_min_celsius"], 60.0)
        self.assertEqual(metrics["avalon_chip_temp_avg_celsius"], 62.5)
        self.assertEqual(metrics["avalon_chip_temp_max_celsius"], 65.0)
        self.assertAlmostEqual(metrics["avalon_chip_voltage_min_volts"], 3.03)
        self.assertAlmostEqual(metrics["avalon_chip_voltage_avg_volts"], 3.055)
        self.assertAlmostEqual(metrics["avalon_chip_voltage_max_volts"], 3.08)
        self.assertEqual(metrics["avalon_chip_matching_work_sum"], 21.0)

    def test_version_info_keeps_1047_model_and_product(self):
        info = exporter.extract_version_info_from_section(VERSION_1047)

        self.assertEqual(info["model"], "1047")
        self.assertEqual(info["prod"], "AvalonMiner 1047")
        self.assertEqual(info["cgminer"], "4.11.1")
        self.assertEqual(info["api"], "3.7")
        self.assertEqual(info["dna"], "REDACTED")
        self.assertEqual(info["mac"], "REDACTED")


if __name__ == "__main__":
    unittest.main()
