import json
import logging
import tempfile
import unittest
from pathlib import Path

from stocks import pipelines
from stocks.pipelines import MagicFormulaPipeline, ScreeningPipeline


class DummySpider:
    logger = logging.getLogger("test")


class StrategyOutputSchemaTest(unittest.TestCase):
    def test_all_strategies_define_explicit_metadata(self):
        strategy_classes = []
        for obj in vars(pipelines).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, ScreeningPipeline)
                and obj is not ScreeningPipeline
                and getattr(obj, "output_path", None)
            ):
                strategy_classes.append(obj)

        self.assertGreater(len(strategy_classes), 0)

        required = [
            "strategy_name",
            "strategy_description",
            "strategy_methodology_summary",
            "strategy_use_cases",
            "strategy_caveats",
        ]
        for strategy_cls in strategy_classes:
            for field in required:
                self.assertIn(
                    field,
                    strategy_cls.__dict__,
                    f"{strategy_cls.__name__} must define {field}",
                )

            self.assertTrue(strategy_cls.strategy_name.strip())
            self.assertTrue(strategy_cls.strategy_description.strip())
            self.assertTrue(strategy_cls.strategy_methodology_summary.strip())
            self.assertIsInstance(strategy_cls.strategy_use_cases, list)
            self.assertGreater(len(strategy_cls.strategy_use_cases), 0)
            self.assertIsInstance(strategy_cls.strategy_caveats, list)
            self.assertGreater(len(strategy_cls.strategy_caveats), 0)

    def test_screening_pipeline_writes_strategy_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "magicformula.json"
            pipeline = MagicFormulaPipeline()
            pipeline.output_path = str(output_path)
            pipeline.process_item(
                {
                    "Papel": "TEST3",
                    "Liq.2meses": 200000,
                    "Cotação": 10,
                    "Dados gerais": {"Setor": "Tecnologia"},
                    "Oscilações": {"Marg. EBIT": 0.2, "ROIC": 0.3},
                    "Indicadores fundamentalistas": {"EV / EBIT": 5},
                },
                DummySpider(),
            )

            pipeline.close_spider(DummySpider())

            payload = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertIsInstance(payload, dict)
            self.assertTrue(payload["strategy_id"])
            self.assertEqual(payload["name"], MagicFormulaPipeline.strategy_name)
            self.assertEqual(payload["description"], MagicFormulaPipeline.strategy_description)
            self.assertEqual(
                payload["methodology_summary"],
                MagicFormulaPipeline.strategy_methodology_summary,
            )
            self.assertTrue(payload["formula_latex"])
            self.assertEqual(payload["use_cases"], MagicFormulaPipeline.strategy_use_cases)
            self.assertEqual(payload["caveats"], MagicFormulaPipeline.strategy_caveats)
            self.assertTrue(payload["generated_at"])
            self.assertEqual(payload["universe_size"], 1)
            self.assertEqual(payload["filtered_size"], 1)
            self.assertEqual(payload["result_size"], 1)
            self.assertEqual(payload["stocks"][0]["Rank EV / EBIT"], 1)
            self.assertEqual(payload["stocks"][0]["Rank ROIC"], 1)
            self.assertEqual(payload["stocks"][0]["Rank Magic Formula"], 2)
            json.dumps(payload, allow_nan=False)
