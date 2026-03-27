import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, cast

from stocks import pipelines as strategy_pipelines
from stocks.pipelines import ScreeningPipeline

REQUIRED_STRATEGY_KEYS = {
    "strategy_id",
    "name",
    "description",
    "methodology_summary",
    "formula_latex",
    "use_cases",
    "caveats",
    "generated_at",
    "universe_size",
    "filtered_size",
    "result_size",
    "stocks",
}


def _is_strategy_payload(data: object) -> bool:
    if not isinstance(data, dict):
        return False

    payload = cast(dict[str, Any], data)

    if not REQUIRED_STRATEGY_KEYS.issubset(payload.keys()):
        return False

    if not isinstance(payload.get("stocks"), list):
        return False

    return isinstance(payload.get("strategy_id"), str) and bool(payload.get("strategy_id"))


def _build_stock_index(strategies: list[dict]) -> dict[str, list[str]]:
    index: dict[str, set[str]] = {}
    for strategy in strategies:
        strategy_id = strategy["strategy_id"]
        for stock in strategy.get("stocks", []):
            if not isinstance(stock, dict):
                continue
            ticker = stock.get("Papel")
            if not isinstance(ticker, str) or not ticker:
                continue
            index.setdefault(ticker, set()).add(strategy_id)

    return {ticker: sorted(ids) for ticker, ids in sorted(index.items())}


def _active_strategy_ids() -> set[str]:
    ids: set[str] = set()
    for obj in vars(strategy_pipelines).values():
        if (
            isinstance(obj, type)
            and issubclass(obj, ScreeningPipeline)
            and obj is not ScreeningPipeline
            and getattr(obj, "output_path", None)
        ):
            ids.add(obj._strategy_id())
    return ids


def build_bundle(input_dir: Path, output_file: Path) -> dict:
    input_dir = Path(input_dir)
    output_file = Path(output_file)

    active_ids = _active_strategy_ids()
    strategies: list[dict] = []
    for file_path in sorted(input_dir.glob("*.json")):
        if file_path == output_file:
            continue

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if not _is_strategy_payload(data):
            continue
        if data.get("strategy_id") not in active_ids:
            continue

        strategies.append(data)

    strategies.sort(key=lambda item: item["strategy_id"])

    bundle = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "strategy_count": len(strategies),
        "strategies": strategies,
        "stock_index": _build_stock_index(strategies),
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Build frontend strategy bundle")
    parser.add_argument(
        "--input",
        default="data/strategies",
        help="Directory containing strategy JSON files",
    )
    parser.add_argument(
        "--output",
        default="frontend/data/strategies.bundle.json",
        help="Bundle output file",
    )
    args = parser.parse_args()

    build_bundle(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
