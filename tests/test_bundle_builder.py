import json
import tempfile
import unittest
from pathlib import Path

from stocks.bundle import build_bundle


class BundleBuilderTest(unittest.TestCase):
    def test_bundle_includes_only_valid_strategy_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            output = base / "frontend" / "data" / "strategies.bundle.json"

            valid = {
                "strategy_id": "magicformula",
                "name": "Magic Formula",
                "description": "desc",
                "methodology_summary": "summary",
                "use_cases": ["x"],
                "caveats": ["y"],
                "generated_at": "2026-03-27T00:00:00+00:00",
                "universe_size": 100,
                "filtered_size": 50,
                "result_size": 2,
                "stocks": [{"Papel": "PETR4"}, {"Papel": "VALE3"}],
            }

            (base / "magicformula.json").write_text(json.dumps(valid), encoding="utf-8")
            (base / "fundamentus.json").write_text(json.dumps([{"Papel": "PETR4"}]), encoding="utf-8")
            (base / "broken.json").write_text(json.dumps({"strategy_id": "broken"}), encoding="utf-8")

            bundle = build_bundle(base, output)
            self.assertEqual(len(bundle["strategies"]), 1)
            self.assertEqual(bundle["strategies"][0]["strategy_id"], "magicformula")
            self.assertTrue(output.exists())

    def test_bundle_builds_stock_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            output = base / "frontend" / "data" / "strategies.bundle.json"

            m = {
                "strategy_id": "magicformula",
                "name": "Magic Formula",
                "description": "desc",
                "methodology_summary": "summary",
                "use_cases": ["x"],
                "caveats": ["y"],
                "generated_at": "2026-03-27T00:00:00+00:00",
                "universe_size": 100,
                "filtered_size": 50,
                "result_size": 2,
                "stocks": [{"Papel": "PETR4"}, {"Papel": "VALE3"}],
            }
            q = {
                "strategy_id": "quality",
                "name": "Quality",
                "description": "desc",
                "methodology_summary": "summary",
                "use_cases": ["x"],
                "caveats": ["y"],
                "generated_at": "2026-03-27T00:00:00+00:00",
                "universe_size": 100,
                "filtered_size": 55,
                "result_size": 1,
                "stocks": [{"Papel": "PETR4"}],
            }

            (base / "magicformula.json").write_text(json.dumps(m), encoding="utf-8")
            (base / "quality.json").write_text(json.dumps(q), encoding="utf-8")

            bundle = build_bundle(base, output)
            self.assertEqual(bundle["stock_index"]["PETR4"], ["magicformula", "quality"])
            self.assertEqual(bundle["stock_index"]["VALE3"], ["magicformula"])


if __name__ == "__main__":
    unittest.main()
