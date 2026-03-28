"""
StatusInvest cross-validation spider.

Scrapes key financial metrics from StatusInvest for tickers previously
collected by the Fundamentus spider. Outputs a cross-validation report
comparing metrics between sources to flag data quality discrepancies.

Usage:
    scrapy crawl statusinvest
    # Or limit to specific tickers:
    scrapy crawl statusinvest -a tickers=VULC3,WEGE3,PETR4
"""

import json
import logging
from pathlib import Path

import scrapy

logger = logging.getLogger(__name__)

FUNDAMENTUS_OUTPUT = "data/raw/fundamentus.json"
CROSSVAL_OUTPUT = "data/intelligence/cross_validation.json"

# Metrics to compare: (display_name, fundamentus_path, statusinvest_h3_title, is_percentage)
METRICS_MAP = [
    ("P/L", ("Indicadores fundamentalistas", "P/L"), "P/L", False),
    ("P/VP", ("Indicadores fundamentalistas", "P/VP"), "P/VP", False),
    ("ROE", ("Oscilações", "ROE"), "ROE", True),
    ("Marg. Líquida", ("Oscilações", "Marg. Líquida"), "M. Líquida", True),
    ("Div. Yield", ("Indicadores fundamentalistas", "Div. Yield"), "D.Y", True),
    ("ROIC", ("Oscilações", "ROIC"), "ROIC", True),
    ("Marg. EBIT", ("Oscilações", "Marg. EBIT"), "M. EBIT", True),
    ("Liquidez Corr", ("Oscilações", "Liquidez Corr"), "Liq. corrente", False),
    ("EV/EBIT", ("Indicadores fundamentalistas", "EV / EBIT"), "EV/EBIT", False),
    ("M. Bruta", ("Oscilações", "Marg. Bruta"), "M. Bruta", True),
]

TOLERANCE = 0.15  # 15% relative tolerance


class StatusInvestSpider(scrapy.Spider):
    name = "statusinvest"
    allowed_domains = ["statusinvest.com.br"]

    custom_settings = {
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS": 2,
        "ROBOTSTXT_OBEY": True,
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "pt-BR,pt;q=0.9",
        },
    }

    def __init__(self, tickers=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fundamentus_data: dict[str, dict] = {}
        self.comparisons: list[dict] = []
        self.ticker_filter: set[str] | None = None
        if tickers:
            self.ticker_filter = {t.strip().upper() for t in str(tickers).split(",")}

    def start_requests(self):
        fundamentus_path = Path(FUNDAMENTUS_OUTPUT)
        if not fundamentus_path.exists():
            logger.error("Fundamentus data not found at %s. Run 'just crawl' first.", FUNDAMENTUS_OUTPUT)
            return

        data = json.loads(fundamentus_path.read_text(encoding="utf-8"))
        for item in data:
            ticker = item.get("Papel", "")
            if ticker:
                self.fundamentus_data[ticker] = item

        tickers = list(self.fundamentus_data.keys())
        if self.ticker_filter:
            tickers = [t for t in tickers if t in self.ticker_filter]

        logger.info("Cross-validating %d tickers against StatusInvest", len(tickers))

        for ticker in tickers:
            url = f"https://statusinvest.com.br/acoes/{ticker.lower()}"
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={"ticker": ticker},
                errback=self.handle_error,
            )

    def _parse_br_number(self, text):
        """Parse Brazilian number format from StatusInvest."""
        if not text:
            return None
        cleaned = text.strip().replace(".", "").replace(",", ".").replace("%", "")
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _get_fundamentus_value(self, item, path):
        """Get a value from the Fundamentus data given a (section, key) path."""
        from stocks.pipelines import ScreeningPipeline

        section, key = path
        raw = ScreeningPipeline._get_nested(item, section, key)
        if raw is None:
            return None
        return ScreeningPipeline._as_number(raw, None)

    def _extract_indicator_value(self, response, h3_title):
        """Extract indicator value by finding the h3 title and the nearby strong.value element."""
        import re

        # HTML-encode special chars for matching
        escaped_title = h3_title.replace("í", "&#xED;")

        # Try both raw and escaped versions
        for title_variant in [h3_title, escaped_title]:
            pattern = rf'uppercase">{re.escape(title_variant)}</h3>'
            match = re.search(pattern, response.text, re.IGNORECASE)
            if match:
                # Look for the value in the next ~400 chars
                chunk = response.text[match.end():match.end() + 400]
                val_match = re.search(r'class="value[^"]*">([\d,.\-%]+)</strong>', chunk)
                if val_match:
                    return self._parse_br_number(val_match.group(1))
        return None

    def parse(self, response):
        ticker = response.meta["ticker"]
        fund_item = self.fundamentus_data.get(ticker, {})

        if response.status != 200:
            logger.warning("StatusInvest returned %d for %s", response.status, ticker)
            return

        comparison = {
            "ticker": ticker,
            "sector": fund_item.get("Setor"),
            "metrics": [],
            "discrepancies": [],
        }

        for display_name, fund_path, si_title, is_pct in METRICS_MAP:
            fund_val = self._get_fundamentus_value(fund_item, fund_path)
            si_val = self._extract_indicator_value(response, si_title)

            # StatusInvest shows percentages as 48.00 (meaning 48%), Fundamentus as 0.48
            if is_pct and si_val is not None:
                si_val = si_val / 100.0

            metric_entry = {
                "name": display_name,
                "fundamentus": round(fund_val, 4) if fund_val is not None else None,
                "statusinvest": round(si_val, 4) if si_val is not None else None,
            }

            # Check for discrepancy
            if fund_val is not None and si_val is not None:
                if fund_val == 0 and si_val == 0:
                    metric_entry["match"] = True
                elif fund_val == 0 or si_val == 0:
                    metric_entry["match"] = False
                    metric_entry["diff_pct"] = None
                else:
                    diff = abs(fund_val - si_val) / max(abs(fund_val), abs(si_val))
                    metric_entry["diff_pct"] = round(diff * 100, 1)
                    metric_entry["match"] = diff <= TOLERANCE

                if not metric_entry.get("match", True):
                    comparison["discrepancies"].append(display_name)

            comparison["metrics"].append(metric_entry)

        self.comparisons.append(comparison)

    def handle_error(self, failure):
        ticker = failure.request.meta.get("ticker", "unknown")
        logger.warning("Failed to fetch StatusInvest for %s: %s", ticker, failure.getErrorMessage())

    def closed(self, reason):
        if not self.comparisons:
            logger.warning("No cross-validation data collected")
            return

        self.comparisons.sort(key=lambda x: len(x["discrepancies"]), reverse=True)

        total_discrepancies = sum(len(c["discrepancies"]) for c in self.comparisons)
        stocks_with_issues = sum(1 for c in self.comparisons if c["discrepancies"])

        payload = {
            "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "source_a": "Fundamentus",
            "source_b": "StatusInvest",
            "tolerance_pct": TOLERANCE * 100,
            "tickers_compared": len(self.comparisons),
            "tickers_with_discrepancies": stocks_with_issues,
            "total_discrepancies": total_discrepancies,
            "comparisons": self.comparisons,
        }

        output_path = Path(CROSSVAL_OUTPUT)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)

        logger.info(
            "Cross-validation: %d/%d tickers have discrepancies (%d total)",
            stocks_with_issues,
            len(self.comparisons),
            total_discrepancies,
        )
