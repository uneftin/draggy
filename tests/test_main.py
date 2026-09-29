import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from main import LiveData, PerformanceStats, create_handler, parse_gprmc, run


def sentence(time_text="120000.000", speed_knots="0.0", status="A"):
    body = (
        f"GPRMC,{time_text},{status},3150.7238,N,03411.7278,E,"
        f"{speed_knots},0.00,190926,,,A"
    )
    checksum = 0
    for character in body:
        checksum ^= ord(character)
    return f"${body}*{checksum:02X}"


def reading(second, speed):
    moment = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc) + timedelta(seconds=second)
    return {
        "timestamp": moment.isoformat().replace("+00:00", "Z"),
        "latitude": 31.8,
        "longitude": 34.8,
        "speed_kmh": speed,
        "course_degrees": 0.0,
    }


class ParserTests(unittest.TestCase):
    def test_parses_valid_rmc_and_converts_units(self):
        result = parse_gprmc(sentence(speed_knots="10.0"))
        self.assertEqual(result["speed_kmh"], 18.52)
        self.assertAlmostEqual(result["latitude"], 31.8453967)
        self.assertAlmostEqual(result["longitude"], 34.1954633)

    def test_rejects_bad_checksum(self):
        with self.assertRaisesRegex(ValueError, "checksum"):
            parse_gprmc(sentence()[:-2] + "00")

    def test_rejects_no_fix(self):
        with self.assertRaisesRegex(ValueError, "active fix"):
            parse_gprmc(sentence(status="V"))


class StatsTests(unittest.TestCase):
    def test_calculates_live_and_best_stats(self):
        stats = PerformanceStats()
        stats.update(reading(0, 0))
        value = stats.update(reading(5, 100))
        self.assertEqual(value["stats"]["top_speed_kmh"], 100)
        self.assertEqual(value["stats"]["best_times_seconds"]["0_100"], 5.0)
        self.assertAlmostEqual(value["stats"]["acceleration_mps2"], 5.556, places=3)
        self.assertAlmostEqual(value["stats"]["max_g"], 0.567, places=3)

    def test_keeps_the_fastest_run(self):
        stats = PerformanceStats()
        for item in (reading(0, 0), reading(6, 100), reading(10, 0), reading(14, 100)):
            value = stats.update(item)
        self.assertEqual(value["stats"]["best_times_seconds"]["0_100"], 4.0)


class IntegrationTests(unittest.TestCase):
    def test_logs_and_publishes_valid_lines(self):
        live_data = LiveData()
        with tempfile.TemporaryDirectory() as directory:
            log_file = Path(directory) / "gps.jsonl"
            run(["not NMEA", sentence()], live_data, log_file)
            lines = log_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIsNotNone(json.loads(lines[0])["reading"])
        self.assertEqual(live_data.latest()[0], 1)

    def test_stats_http_endpoint(self):
        live_data = LiveData()
        live_data.publish({"reading": {"speed_kmh": 42}, "stats": {"top_speed_kmh": 42}})
        server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(live_data))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{server.server_port}/stats", timeout=2
            ) as response:
                value = json.load(response)
            self.assertEqual(value["stats"]["top_speed_kmh"], 42)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
