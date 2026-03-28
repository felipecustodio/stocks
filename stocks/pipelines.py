import datetime as dt
import json
import logging
import math
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class NormalizeValuesPipeline:
    def parse_float(self, value):
        """Convert a Brazilian formatted float string to a Python float."""
        if not value or value in {"-", "\n-"}:
            return None
        # Remove any unwanted characters and replace comma with dot
        value = re.sub(r"[^\d,.-]", "", value)
        value = value.replace(".", "").replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return None

    def parse_percentage(self, value):
        """Convert a percentage string to a Python float."""
        if not value or value in {"-", "\n-"}:
            return None
        # Remove unwanted characters and extract percentage
        value = re.sub(r"[^\d,.-]", "", value)
        value = value.replace(".", "").replace(",", ".")
        try:
            return float(value) / 100
        except ValueError:
            return None

    def process_dictionary(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, str):
                if "%" in value:
                    dictionary[key] = self.parse_percentage(value)
                else:
                    # If it starts with a number or "-", and does not have "/" (date), convert to float
                    if re.match(r"^-?\d", value) and "/" not in value:
                        dictionary[key] = self.parse_float(value)
            if isinstance(value, dict):
                self.process_dictionary(value)
        return dictionary

    def process_item(self, item, spider):
        item = self.process_dictionary(item)
        return item

class CleanValuesPipeline:
    def process_dictionary(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, str):
                dictionary[key] = value.strip()
                dictionary[key] = value.replace("\n", "")
            elif isinstance(value, dict):
                self.process_dictionary(value)
        return dictionary

    def process_item(self, item, spider):
        item = self.process_dictionary(item)
        return item

class NanValuesPipeline:
    def process_dictionary(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                self.process_dictionary(value)
            elif value in {"", "-", None} or (
                key in ["Papel", "Tipo", "Empresa", "Setor", "Subsetor", "Data últ cot"] and not value
            ):
                dictionary[key] = None
        return dictionary

    def process_item(self, item, spider):
        item = self.process_dictionary(item)
        return item

class DateValuesPipeline:
    def process_dictionary(self, dictionary, spider):
        for key, value in dictionary.items():
            if key in ["Data últ cot", "Data", "Últ balanço processado"] and value is not None and value != "-":
                try:
                    dictionary[key] = dt.datetime.strptime(value, "%d/%m/%Y").strftime("%Y-%m-%d")
                except Exception as e:
                    spider.logger.error(f"Error parsing date: {e}")
        return dictionary

    def process_item(self, item, spider):
        item = self.process_dictionary(item, spider)
        return item


DATA_SOURCES = {
    "Fundamentus": "https://www.fundamentus.com.br/detalhes.php?papel={ticker}",
    "StatusInvest": "https://statusinvest.com.br/acoes/{ticker_lower}",
    "Investidor10": "https://investidor10.com.br/acoes/{ticker_lower}/",
    "Yahoo Finance": "https://finance.yahoo.com/quote/{ticker}.SA/",
    "Google Finance": "https://www.google.com/finance/quote/{ticker}:BVMF",
    "TradingView": "https://www.tradingview.com/symbols/BMFBOVESPA-{ticker}/",
}


class DataSourcesPipeline:
    """Enriches each stock item with reference URLs to major financial data sources."""

    def process_item(self, item, spider):
        ticker = item.get("Papel", "")
        if ticker:
            item["Fontes"] = {
                name: url.format(ticker=ticker, ticker_lower=ticker.lower())
                for name, url in DATA_SOURCES.items()
            }
        return item


class AnomalyDetectionPipeline:
    """Detects data quality anomalies and flags suspicious metrics per ticker.

    Runs statistical outlier detection on key financial metrics,
    consistency checks between related fields, and impossible-value detection.
    Outputs a data quality report to data/intelligence/anomalies.json.
    """

    output_path = "data/intelligence/anomalies.json"

    # Metric definitions: (section, key, min_sane, max_sane, description)
    METRIC_BOUNDS = [
        ("Oscilações", "ROE", -1.0, 1.5, "ROE fora da faixa -100% a 150%"),
        ("Oscilações", "ROIC", -1.0, 1.0, "ROIC fora da faixa -100% a 100%"),
        ("Oscilações", "Marg. Líquida", -2.0, 1.0, "Margem Líquida fora da faixa -200% a 100%"),
        ("Oscilações", "Marg. Bruta", -0.5, 1.0, "Margem Bruta fora da faixa -50% a 100%"),
        ("Oscilações", "Marg. EBIT", -2.0, 1.0, "Margem EBIT fora da faixa -200% a 100%"),
        ("Indicadores fundamentalistas", "P/L", -500, 500, "P/L extremo"),
        ("Indicadores fundamentalistas", "EV / EBIT", -100, 200, "EV/EBIT extremo"),
    ]

    def __init__(self):
        self.items = []

    @staticmethod
    def _as_number(value, default=0.0):
        return ScreeningPipeline._as_number(value, default)

    @staticmethod
    def _get_nested(item, section, key, default=None):
        return ScreeningPipeline._get_nested(item, section, key, default)

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

    def _check_bounds(self, item):
        """Check if metrics fall within sane bounds."""
        flags = []
        for section, key, min_val, max_val, desc in self.METRIC_BOUNDS:
            value = self._as_number(self._get_nested(item, section, key, None), None)
            if value is None:
                continue
            if value < min_val or value > max_val:
                flags.append({
                    "type": "out_of_bounds",
                    "metric": key,
                    "value": value,
                    "bounds": [min_val, max_val],
                    "description": desc,
                })
        return flags

    def _check_consistency(self, item):
        """Check for inconsistencies between related metrics."""
        flags = []

        # Net margin should not exceed gross margin
        gross = self._as_number(self._get_nested(item, "Oscilações", "Marg. Bruta", None), None)
        net = self._as_number(self._get_nested(item, "Oscilações", "Marg. Líquida", None), None)
        if gross is not None and net is not None and net > gross > 0:
            flags.append({
                "type": "inconsistency",
                "metric": "Marg. Líquida > Marg. Bruta",
                "values": {"Marg. Bruta": gross, "Marg. Líquida": net},
                "description": "Margem líquida maior que margem bruta sugere receita financeira inflando lucro",
            })

        # EV/EBIT < 1 is highly suspicious for non-financial companies
        ev_ebit = self._as_number(
            self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", None), None
        )
        if ev_ebit is not None and 0 < ev_ebit < 1:
            flags.append({
                "type": "suspicious_value",
                "metric": "EV / EBIT",
                "value": ev_ebit,
                "description": (
                    "EV/EBIT < 1 geralmente indica EV distorcido "
                    "(ex: empresa financeira ou caixa excessivo)"
                ),
            })

        # Lucro Líquido TTM should be roughly consistent with LPA * Nro. Ações
        demos = item.get("Dados demonstrativos de resultados", {})
        if isinstance(demos, dict):
            ttm = demos.get("Últimos 12 meses", {})
            if isinstance(ttm, dict):
                lucro_ttm = self._as_number(ttm.get("Lucro Líquido", None), None)
                nro_acoes = self._as_number(item.get("Nro. Ações", None), None)
                lpa = self._as_number(self._get_nested(item, "Oscilações", "LPA", None), None)
                if lucro_ttm is not None and nro_acoes and nro_acoes > 0 and lpa is not None:
                    implied_lucro = lpa * nro_acoes
                    if implied_lucro != 0:
                        ratio = lucro_ttm / implied_lucro
                        if ratio > 1.5 or ratio < 0.5:
                            flags.append({
                                "type": "inconsistency",
                                "metric": "Lucro TTM vs LPA * Nro. Ações",
                                "values": {
                                    "Lucro TTM": lucro_ttm,
                                    "LPA * Nro. Ações": round(implied_lucro, 2),
                                    "ratio": round(ratio, 2),
                                },
                                "description": (
                                    "Lucro TTM diverge significativamente do implícito por LPA, "
                                    "possível item não recorrente ou erro de dados"
                                ),
                            })

        return flags

    def _compute_zscore_flags(self, items):
        """Flag metrics that are statistical outliers (|z-score| > 3)."""
        metrics_to_check = [
            ("Oscilações", "ROE"),
            ("Oscilações", "ROIC"),
            ("Oscilações", "Marg. Líquida"),
            ("Indicadores fundamentalistas", "EV / EBIT"),
        ]

        ticker_flags: dict[str, list] = {}

        for section, key in metrics_to_check:
            values = []
            for item in items:
                val = self._as_number(self._get_nested(item, section, key, None), None)
                if val is not None:
                    values.append((item.get("Papel", ""), val))

            if len(values) < 10:
                continue

            nums = [v for _, v in values]
            mean = sum(nums) / len(nums)
            variance = sum((x - mean) ** 2 for x in nums) / len(nums)
            std = variance**0.5

            if std == 0:
                continue

            for ticker, val in values:
                zscore = (val - mean) / std
                if abs(zscore) > 3:
                    flag = {
                        "type": "statistical_outlier",
                        "metric": key,
                        "value": val,
                        "z_score": round(zscore, 2),
                        "population_mean": round(mean, 4),
                        "population_std": round(std, 4),
                        "description": f"{key} com z-score de {zscore:.1f} (> 3 desvios da média)",
                    }
                    ticker_flags.setdefault(ticker, []).append(flag)

        return ticker_flags

    def close_spider(self, spider):
        if not self.items:
            return

        anomalies = {}

        # Per-item checks
        for item in self.items:
            ticker = item.get("Papel", "")
            if not ticker:
                continue

            flags = self._check_bounds(item) + self._check_consistency(item)
            if flags:
                anomalies[ticker] = {
                    "ticker": ticker,
                    "sector": item.get("Setor"),
                    "flags": flags,
                    "fontes": item.get("Fontes", {}),
                }

        # Z-score outlier detection
        zscore_flags = self._compute_zscore_flags(self.items)
        for ticker, flags in zscore_flags.items():
            if ticker in anomalies:
                anomalies[ticker]["flags"].extend(flags)
            else:
                item = next((i for i in self.items if i.get("Papel") == ticker), {})
                anomalies[ticker] = {
                    "ticker": ticker,
                    "sector": item.get("Setor"),
                    "flags": flags,
                    "fontes": item.get("Fontes", {}),
                }

        # Sort by number of flags (most problematic first)
        sorted_anomalies = sorted(anomalies.values(), key=lambda x: len(x["flags"]), reverse=True)

        # Severity classification
        for entry in sorted_anomalies:
            n = len(entry["flags"])
            entry["severity"] = "high" if n >= 3 else "medium" if n >= 2 else "low"

        payload = {
            "generated_at": dt.datetime.now(dt.UTC).isoformat(),
            "universe_size": len(self.items),
            "anomalies_detected": len(sorted_anomalies),
            "severity_counts": {
                "high": sum(1 for a in sorted_anomalies if a["severity"] == "high"),
                "medium": sum(1 for a in sorted_anomalies if a["severity"] == "medium"),
                "low": sum(1 for a in sorted_anomalies if a["severity"] == "low"),
            },
            "stocks": sorted_anomalies,
        }

        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)

        logger.info(
            "AnomalyDetectionPipeline: %d anomalies detected (%d high, %d medium, %d low)",
            len(sorted_anomalies),
            payload["severity_counts"]["high"],
            payload["severity_counts"]["medium"],
            payload["severity_counts"]["low"],
        )


EXCLUDED_SECTORS = [
    "Holdings Diversificadas",
    "Intermediários Financeiros",
    "Previdência e Seguros",
    "Serviços Financeiros Diversos",
]


class ScreeningPipeline:
    """Base class for stock screening pipelines.

    Collects all items during the crawl, then filters and ranks on spider close.
    Subclasses implement `rank` to define their ranking strategy.
    """

    MIN_LIQUIDITY = 150_000
    output_path: str
    strategy_name: str | None = None
    strategy_description: str | None = None
    strategy_methodology_summary: str | None = None
    strategy_formula_latex: str | None = None
    strategy_use_cases: list[str] | None = None
    strategy_caveats: list[str] | None = None

    def __init__(self):
        self.items = []

    @staticmethod
    def _as_number(value, default=0.0):
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = re.sub(r"[^\d,.\-]", "", value.strip())
            if not cleaned or cleaned == "-":
                return default
            if "," in cleaned and "." in cleaned:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            elif "," in cleaned:
                cleaned = cleaned.replace(",", ".")
            try:
                return float(cleaned)
            except ValueError:
                return default
        return default

    @staticmethod
    def _get_nested(item, section, key, default=None):
        section_data = item.get(section)
        if isinstance(section_data, dict):
            return section_data.get(key, default)
        return default

    @staticmethod
    def _get_liquidity(item):
        value = item.get("Liq.2meses", 0)
        return ScreeningPipeline._as_number(value, 0.0)

    def _get_sector(self, item):
        return item.get("Setor")

    def filter(self, items):
        return [
            item for item in items
            if self._get_liquidity(item) >= self.MIN_LIQUIDITY
            and self._as_number(self._get_nested(item, "Oscilações", "Marg. EBIT", float("-inf")), float("-inf")) > 0
            and self._get_sector(item) not in EXCLUDED_SECTORS
        ]

    def rank(self, items):
        raise NotImplementedError

    @classmethod
    def _strategy_id(cls):
        output_path = getattr(cls, "output_path", "") or ""
        if output_path:
            return output_path.rsplit("/", 1)[-1].removesuffix(".json")
        return cls.__name__.removesuffix("Pipeline").lower()

    @classmethod
    def _strategy_name(cls):
        if cls.strategy_name:
            return cls.strategy_name
        tokens = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+", cls.__name__.removesuffix("Pipeline"))
        return " ".join(tokens) if tokens else cls.__name__

    @classmethod
    def _strategy_description(cls):
        if cls.strategy_description:
            return cls.strategy_description
        docstring = (cls.__doc__ or "").strip()
        if not docstring:
            return cls._strategy_name()
        return " ".join(docstring.split())

    @classmethod
    def _strategy_methodology_summary(cls):
        if cls.strategy_methodology_summary:
            return cls.strategy_methodology_summary
        return (
            "Applies the shared liquidity, margin, and sector filters, then ranks the remaining stocks using "
            f"{cls._strategy_name()}-specific metrics."
        )

    @classmethod
    def _strategy_formula_latex(cls):
        if cls.strategy_formula_latex:
            return cls.strategy_formula_latex

        formulas = {
            "magicformula": r"\mathrm{Score}=Rank(EV/EBIT)+Rank(ROIC)",
            "cdv": r"Rank\uparrow\left(\frac{1}{EV/EBIT}\right)",
            "intersection": r"\mathcal{S}=\mathcal{S}_{MagicFormula}\cap\mathcal{S}_{CDV}",
            "graham": r"GN=\sqrt{22.5\cdot LPA\cdot VPA},\ MOS=\frac{GN-P}{GN},\ P<GN",
            "bazin": r"DY\ge 0.06,\ \frac{Divida}{Patrimonio}\le 1,\ Rank\downarrow DY",
            "quality": r"\mathrm{Score}=Rank(ROIC)+Rank(MargemLiquida)",
            "piotroski": r"F=\sum_{i=1}^{9}\mathbf{1}\{sinal_i\},\ F\ge 6",
            "multifactor": r"\mathrm{Score}=0.30R_v+0.30R_q+0.20R_g+0.20R_i",
            "acquirers": r"Rank\uparrow\left(\frac{1}{EV/EBITDA}\right)",
            "deepvalue": r"\mathrm{Score}=R_{P/L}+R_{P/VP}+R_{PSR}+R_{EV/EBITDA}",
            "netnet": r"NCAV=AC-(A-PL),\ P<\frac{NCAV}{N},\ Rank\downarrow\left(-\frac{P}{NCAV/N}\right)",
            "garp": r"PEG=\frac{P/L}{100\cdot Cresc_{5a}},\ Rank\downarrow PEG",
            "momentum_value": r"\mathrm{Score}=Rank(-Momentum_{12m})+Rank(P/VP)",
            "contrarian": r"\frac{P-Min52w}{Min52w}\le 0.20,\ ROIC\ge 0.10,\ \frac{Divida}{Patrimonio}\le 1.5",
            "cashrich": r"\mathrm{Score}=\frac{Caixa}{ValorMercado},\ Rank\downarrow(-Score)",
            "dupont": r"\mathrm{Score}=Rank(MargemLiquida)+Rank(GiroAtivos)+Rank(Alavancagem)",
            "smallcap_value": r"ValorMercado\le Q1,\ Rank\downarrow(EV/EBIT)",
            "largecap_dividend": (
                r"ValorMercado\ge Q3,\ DY\ge 0.04,\ "
                r"\frac{Divida}{Patrimonio}\le 1,\ Rank\downarrow DY"
            ),
            "sector_relative": r"RankSetor(EV/EBIT)\le Q1_{setor}",
            "earnings_accel": r"EA=\frac{4\cdot Lucro_{3m}}{Lucro_{12m}},\ Rank\downarrow EA",
            "assetlight": r"\mathrm{Score}=Rank(ROIC)+Rank(GiroAtivos)",
            "altman": (
                r"Z=3.3\cdot\frac{EBIT}{Ativo}+1.0\cdot"
                r"\frac{ValorMercado}{PassivoTotal}+1.0\cdot GiroAtivos,\ Z\ge 1.8"
            ),
            "bookvalue": r"0<P/VP<1,\ Desconto=1-P/VP,\ Rank\downarrow Desconto",
            "working_capital": r"\mathrm{Score}=Rank(P/Cap.Giro)+Rank(P/AtivCircLiq)",
            "margin_compression": r"Gap=Marg.Bruta-Marg.EBIT,\ Rank\downarrow Gap",
            "fortress": r"LiqCorr>1.5,\ Div/Patrim<0.5,\ Score=Rank(LiqCorr)+Rank(Div/Patrim)",
            "redflags": r"Flags=\sum\mathbf{1}\{sinal_i\},\ Flags\ge 2,\ Rank\downarrow Flags",
            "earnings_yield_spread": r"EY=\frac{1}{EV/EBIT},\ Spread=EY-Selic,\ Rank\downarrow Spread",
            "buffett": r"ROE>0.15,\ Div/Patrim<1,\ MargLiq>0.10,\ 0<P/L<25",
            "volatility_adjusted": r"Vol=\frac{Max52-Min52}{Min52},\ Score=\frac{EV}{EBIT}\cdot(1+Vol)",
            "consensus": r"Appearances=\sum_{s}\mathbf{1}\{ticker\in S_s\},\ Appearances\ge 5",
        }
        return formulas.get(
            cls._strategy_id(),
            r"\text{Filtro base} \rightarrow \text{ranking por métricas específicas da estratégia}",
        )

    @classmethod
    def _strategy_use_cases(cls):
        if cls.strategy_use_cases:
            return cls.strategy_use_cases
        return [
            "Compare the strategy's top candidates after a single crawl.",
            "Feed the screened output into a frontend or downstream analysis tool.",
        ]

    @classmethod
    def _strategy_caveats(cls):
        if cls.strategy_caveats:
            return cls.strategy_caveats
        return [
            "Ranking depends on the quality and freshness of the underlying Fundamentus data.",
            "Shared filters may exclude companies that otherwise fit the strategy thesis.",
        ]

    def _build_output_payload(self, universe, filtered, ranked):
        payload = {
            "strategy_id": self._strategy_id(),
            "name": self._strategy_name(),
            "description": self._strategy_description(),
            "methodology_summary": self._strategy_methodology_summary(),
            "formula_latex": self._strategy_formula_latex(),
            "use_cases": self._strategy_use_cases(),
            "caveats": self._strategy_caveats(),
            "generated_at": dt.datetime.now(dt.UTC).isoformat(),
            "universe_size": len(universe),
            "filtered_size": len(filtered),
            "result_size": len(ranked),
            "stocks": ranked,
        }
        return self._sanitize_json_value(payload)

    @classmethod
    def _sanitize_json_value(cls, value):
        if isinstance(value, dict):
            return {k: cls._sanitize_json_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [cls._sanitize_json_value(v) for v in value]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        if not self.items:
            return

        filtered = self.filter(self.items)
        logger.info("%s: %d -> %d items after filtering",
                    self.__class__.__name__, len(self.items), len(filtered))

        ranked = self.rank(filtered)
        payload = self._build_output_payload(self.items, filtered, ranked)

        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4, allow_nan=False)

        logger.info("%s: %d ranked stocks written to %s",
                    self.__class__.__name__, len(ranked), self.output_path)


class MagicFormulaPipeline(ScreeningPipeline):
    """Magic Formula (Joel Greenblatt): ranks by combined EV/EBIT + ROIC."""

    output_path = "data/strategies/magicformula.json"
    strategy_name = "Magic Formula"
    strategy_description = "Combina empresas baratas por EV/EBIT com alta eficiência de capital (ROIC)."
    strategy_methodology_summary = (
        "Ranqueia EV/EBIT (menor melhor) e ROIC (maior melhor), depois soma os dois ranks."
    )
    strategy_use_cases = [
        "Montar shortlist de valor + qualidade.",
        "Comparar consenso entre múltiplos e retorno sobre capital.",
    ]
    strategy_caveats = [
        "Pode favorecer setores cíclicos em momentos específicos do ciclo.",
        "Não considera preço recente (momentum) nem risco de concentração.",
    ]

    def rank(self, items):
        for item in items:
            item["_ev_ebit"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", float("inf")),
                float("inf"),
            )
            item["_roic"] = self._as_number(
                self._get_nested(item, "Oscilações", "ROIC", float("-inf")),
                float("-inf"),
            )

        items.sort(key=lambda x: x["_ev_ebit"])
        for rank, item in enumerate(items, 1):
            item["Rank EV / EBIT"] = rank

        items.sort(key=lambda x: x["_roic"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank ROIC"] = rank

        for item in items:
            item["Rank Magic Formula"] = item["Rank EV / EBIT"] + item["Rank ROIC"]
            del item["_ev_ebit"]
            del item["_roic"]

        items.sort(key=lambda x: x["Rank Magic Formula"])
        return items


class CDVPipeline(ScreeningPipeline):
    """Clube do Valor (Ramiro Gomes): ranks by EV/EBIT only."""

    output_path = "data/strategies/cdv.json"
    strategy_name = "CDV (EV/EBIT)"
    strategy_description = "Estratégia de valor focada apenas em EV/EBIT, priorizando empresas mais baratas."
    strategy_methodology_summary = "Ordena ações por EV/EBIT crescente após filtros básicos de liquidez e margem."
    strategy_use_cases = [
        "Selecionar ações com múltiplo operacional baixo.",
        "Usar como carteira de valor simples e transparente.",
    ]
    strategy_caveats = [
        "Um único fator pode aumentar risco de armadilhas de valor.",
        "Não diferencia qualidade operacional além dos filtros mínimos.",
    ]

    def rank(self, items):
        for item in items:
            item["_ev_ebit"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", float("inf")),
                float("inf"),
            )

        items.sort(key=lambda x: x["_ev_ebit"])
        for rank, item in enumerate(items, 1):
            item["Rank EV / EBIT"] = rank

        for item in items:
            del item["_ev_ebit"]

        return items


class GrahamNumberPipeline(ScreeningPipeline):
    """Benjamin Graham: ranks by discount to Graham Number.

    Graham Number = sqrt(22.5 * LPA * VPA). Stocks trading below this
    intrinsic value estimate are considered undervalued. Ranked by the
    margin of safety (discount percentage).
    """

    output_path = "data/strategies/graham.json"
    strategy_name = "Graham Number"
    strategy_description = "Busca ações negociando abaixo do valor justo estimado pelo número de Graham."
    strategy_methodology_summary = "Calcula Graham Number por ação e ranqueia maior margem de segurança."
    strategy_use_cases = [
        "Triagem clássica de valor com margem de segurança explícita.",
        "Comparar preço atual vs valor intrínseco simplificado.",
    ]
    strategy_caveats = [
        "Sensível a qualidade contábil de LPA/VPA.",
        "Modelo simplificado pode subestimar empresas de crescimento.",
    ]

    def filter(self, items):
        """Base filter plus require positive LPA and VPA."""
        base = super().filter(items)
        return [
            item for item in base
            if self._as_number(self._get_nested(item, "Oscilações", "LPA", 0), 0.0) > 0
            and self._as_number(self._get_nested(item, "Oscilações", "VPA", 0), 0.0) > 0
        ]

    def rank(self, items):
        for item in items:
            lpa = self._as_number(self._get_nested(item, "Oscilações", "LPA", 0), 0.0)
            vpa = self._as_number(self._get_nested(item, "Oscilações", "VPA", 0), 0.0)
            graham_number = math.sqrt(22.5 * lpa * vpa)
            cotacao = self._as_number(item.get("Cotação", float("inf")), float("inf"))
            item["Graham Number"] = round(graham_number, 2)
            item["Margin of Safety"] = round((graham_number - cotacao) / graham_number, 4) if graham_number > 0 else 0

        # Only keep stocks trading below their Graham Number
        items = [item for item in items if item.get("Cotação", float("inf")) < item["Graham Number"]]
        items.sort(key=lambda x: x["Margin of Safety"], reverse=True)
        return items


class BazinPipeline(ScreeningPipeline):
    """Décio Bazin method: dividend-focused value investing.

    Filters for Div. Yield >= 6%, low debt (Dív. Brut/Patrim <= 1),
    and ranks by highest dividend yield.
    """

    output_path = "data/strategies/bazin.json"
    strategy_name = "Bazin"
    strategy_description = "Estratégia de renda focada em dividend yield alto com controle de endividamento."
    strategy_methodology_summary = "Filtra DY mínimo e dívida controlada, depois ordena por DY decrescente."
    strategy_use_cases = [
        "Selecionar candidatas de renda em carteira.",
        "Priorizar empresas com histórico de distribuição robusta.",
    ]
    strategy_caveats = [
        "Dividendos passados não garantem continuidade futura.",
        "DY alto pode refletir queda de preço por deterioração fundamental.",
    ]
    MIN_DIV_YIELD = 0.06
    MAX_DEBT_RATIO = 1.0

    def filter(self, items):
        base = super().filter(items)
        return [
            item for item in base
            if self._as_number(self._get_nested(item, "Indicadores fundamentalistas", "Div. Yield", 0), 0.0)
            >= self.MIN_DIV_YIELD
            and self._as_number(
                self._get_nested(item, "Oscilações", "Div Br/ Patrim", float("inf")),
                float("inf"),
            )
            <= self.MAX_DEBT_RATIO
        ]

    def rank(self, items):
        for item in items:
            item["_div_yield"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "Div. Yield", 0),
                0.0,
            )

        items.sort(key=lambda x: x["_div_yield"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Bazin"] = rank
            del item["_div_yield"]

        return items


class QualityPipeline(ScreeningPipeline):
    """Quality ranking: ROIC + Net Margin combined score.

    Selects capital-efficient businesses with high profitability,
    regardless of current valuation.
    """

    output_path = "data/strategies/quality.json"
    strategy_name = "Quality"
    strategy_description = "Ranqueia empresas pela combinação de ROIC e margem líquida."
    strategy_methodology_summary = "Soma rank de eficiência de capital (ROIC) e rentabilidade líquida."
    strategy_use_cases = [
        "Encontrar empresas com fundamentos operacionais fortes.",
        "Complementar estratégias de valor com qualidade.",
    ]
    strategy_caveats = [
        "Pode excluir negócios em virada operacional recente.",
        "Não incorpora valuation diretamente no ranking final.",
    ]

    def rank(self, items):
        for item in items:
            item["_roic"] = self._as_number(
                self._get_nested(item, "Oscilações", "ROIC", float("-inf")),
                float("-inf"),
            )
            item["_net_margin"] = self._as_number(
                self._get_nested(item, "Oscilações", "Marg. Líquida", float("-inf")),
                float("-inf"),
            )

        items.sort(key=lambda x: x["_roic"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank ROIC"] = rank

        items.sort(key=lambda x: x["_net_margin"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Marg. Líquida"] = rank

        for item in items:
            item["Rank Quality"] = item["Rank ROIC"] + item["Rank Marg. Líquida"]
            del item["_roic"]
            del item["_net_margin"]

        items.sort(key=lambda x: x["Rank Quality"])
        return items


class PiotroskiPipeline(ScreeningPipeline):
    """Piotroski F-Score (simplified, single-snapshot version).

    Scores 0-9 based on profitability, leverage, and efficiency signals.
    Some signals that require year-over-year comparison are approximated
    using available data (e.g. 5-year revenue growth as a proxy).
    """

    output_path = "data/strategies/piotroski.json"
    strategy_name = "Piotroski (simplificado)"
    strategy_description = (
        "Seleciona empresas com F-Score mínimo usando sinais de lucratividade, alavancagem e eficiência."
    )
    strategy_methodology_summary = "Calcula F-Score simplificado e mantém apenas ações com pontuação mínima."
    strategy_use_cases = [
        "Filtrar qualidade contábil e financeira em valor.",
        "Excluir empresas com sinais fracos de saúde financeira.",
    ]
    strategy_caveats = [
        "Implementação simplificada não replica todos sinais originais anuais.",
        "Dependente de proxies pode gerar falsos positivos/negativos.",
    ]
    MIN_FSCORE = 6

    def _compute_fscore(self, item):
        score = 0

        # Profitability signals
        roe = self._as_number(self._get_nested(item, "Oscilações", "ROE", 0), 0.0)
        roic = self._as_number(self._get_nested(item, "Oscilações", "ROIC", 0), 0.0)
        ebit_ativo = self._as_number(self._get_nested(item, "Oscilações", "EBIT / Ativo", 0), 0.0)

        if roe > 0:
            score += 1  # Positive ROE
        if roic > 0:
            score += 1  # Positive ROIC (proxy for positive operating cash flow)
        if ebit_ativo > 0:
            score += 1  # Positive return on assets

        # Leverage / liquidity signals
        liq_corr = self._as_number(self._get_nested(item, "Oscilações", "Liquidez Corr", 0), 0.0)
        div_br_patrim = self._as_number(
            self._get_nested(item, "Oscilações", "Div Br/ Patrim", float("inf")),
            float("inf"),
        )

        if liq_corr > 1:
            score += 1  # Current ratio > 1
        if div_br_patrim < 1:
            score += 1  # Low debt-to-equity

        # Efficiency signals
        marg_bruta = self._as_number(self._get_nested(item, "Oscilações", "Marg. Bruta", 0), 0.0)
        marg_ebit = self._as_number(self._get_nested(item, "Oscilações", "Marg. EBIT", 0), 0.0)
        giro_ativos = self._as_number(
            self._get_nested(item, "Indicadores fundamentalistas", "Giro Ativos", 0),
            0.0,
        )
        cresc_rec = self._as_number(self._get_nested(item, "Oscilações", "Cres. Rec (5a)", 0), 0.0)

        if marg_bruta > 0.2:
            score += 1  # Healthy gross margin
        if marg_ebit > 0.1:
            score += 1  # Healthy operating margin
        if giro_ativos > 0.5:
            score += 1  # Efficient asset utilization
        if cresc_rec > 0:
            score += 1  # Revenue growth (5-year proxy)

        return score

    def filter(self, items):
        base = super().filter(items)
        for item in base:
            item["F-Score"] = self._compute_fscore(item)
        return [item for item in base if item["F-Score"] >= self.MIN_FSCORE]

    def rank(self, items):
        items.sort(key=lambda x: x["F-Score"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Piotroski"] = rank
        return items


class MultiFactorPipeline(ScreeningPipeline):
    """Multi-factor score: weighted blend of value, quality, growth, and income.

    Default weights: value (EV/EBIT) 30%, quality (ROIC) 30%,
    growth (5y revenue) 20%, income (Div. Yield) 20%.
    """

    output_path = "data/strategies/multifactor.json"
    strategy_name = "Multi-Factor"
    strategy_description = "Combina valor, qualidade, crescimento e renda em score ponderado único."
    strategy_methodology_summary = "Calcula ranks por fator e aplica pesos fixos para gerar score final."
    strategy_use_cases = [
        "Construir seleção mais balanceada entre fatores.",
        "Reduzir dependência de um único critério de ranking.",
    ]
    strategy_caveats = [
        "Pesos fixos podem não funcionar bem em todos regimes de mercado.",
        "Resultados sensíveis à escala e qualidade dos fatores de entrada.",
    ]

    WEIGHT_VALUE = 0.30
    WEIGHT_QUALITY = 0.30
    WEIGHT_GROWTH = 0.20
    WEIGHT_INCOME = 0.20

    def rank(self, items):
        for item in items:
            item["_ev_ebit"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", float("inf")),
                float("inf"),
            )
            item["_roic"] = self._as_number(
                self._get_nested(item, "Oscilações", "ROIC", float("-inf")),
                float("-inf"),
            )
            item["_growth"] = self._as_number(
                self._get_nested(item, "Oscilações", "Cres. Rec (5a)", float("-inf")),
                float("-inf"),
            )
            item["_div_yield"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "Div. Yield", 0),
                0.0,
            )

        # Rank each factor independently
        items.sort(key=lambda x: x["_ev_ebit"])
        for rank, item in enumerate(items, 1):
            item["Rank Value"] = rank

        items.sort(key=lambda x: x["_roic"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Quality"] = rank

        items.sort(key=lambda x: x["_growth"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Growth"] = rank

        items.sort(key=lambda x: x["_div_yield"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Income"] = rank

        # Weighted composite score
        for item in items:
            item["Rank Multi-Factor"] = round(
                item["Rank Value"] * self.WEIGHT_VALUE
                + item["Rank Quality"] * self.WEIGHT_QUALITY
                + item["Rank Growth"] * self.WEIGHT_GROWTH
                + item["Rank Income"] * self.WEIGHT_INCOME
            )
            del item["_ev_ebit"]
            del item["_roic"]
            del item["_growth"]
            del item["_div_yield"]

        items.sort(key=lambda x: x["Rank Multi-Factor"])
        return items


class AcquirersMultiplePipeline(ScreeningPipeline):
    """Tobias Carlisle's Acquirer's Multiple: ranks purely by EV/EBITDA (lower is better)."""

    output_path = "data/strategies/acquirers.json"
    strategy_name = "Acquirer's Multiple"
    strategy_description = "Ranqueia ações por EV/EBITDA (menor melhor), inspirado em Tobias Carlisle."
    strategy_methodology_summary = "Ordena empresas por EV/EBITDA crescente após filtros-base."
    strategy_use_cases = [
        "Buscar empresas baratas por múltiplo de firma sobre EBITDA.",
        "Comparar alternativa ao foco em EV/EBIT.",
    ]
    strategy_caveats = [
        "EBITDA pode mascarar necessidades de capex em alguns setores.",
        "Múltiplo isolado pode aumentar risco de value trap.",
    ]

    def rank(self, items):
        for item in items:
            item["_ev_ebitda"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "EV / EBITDA", float("inf")),
                float("inf"),
            )

        items.sort(key=lambda x: x["_ev_ebitda"])
        for rank, item in enumerate(items, 1):
            item["Rank Acquirer's Multiple"] = rank
            del item["_ev_ebitda"]

        return items


class DeepValuePipeline(ScreeningPipeline):
    """Combined rank of P/L + P/VP + PSR + EV/EBITDA (equal weight). Lower combined rank is better."""

    output_path = "data/strategies/deepvalue.json"
    strategy_name = "Deep Value"
    strategy_description = "Combina múltiplos de valuation para encontrar ações baratas em várias dimensões."
    strategy_methodology_summary = "Soma ranks de P/L, P/VP, PSR e EV/EBITDA com pesos iguais."
    strategy_use_cases = [
        "Identificar barganhas com confirmação por múltiplos distintos.",
        "Aumentar robustez de triagem puramente de valor.",
    ]
    strategy_caveats = [
        "Pode penalizar empresas de qualidade com prêmio estrutural.",
        "Múltiplos baixos podem refletir deterioração real do negócio.",
    ]

    def filter(self, items):
        base = super().filter(items)
        return [
            item for item in base
            if self._as_number(self._get_nested(item, "Indicadores fundamentalistas", "P/L", 0), 0.0) > 0
        ]

    def rank(self, items):
        for item in items:
            item["_pl"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "P/L", float("inf")),
                float("inf"),
            )
            item["_pvp"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "P/VP", float("inf")),
                float("inf"),
            )
            item["_psr"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "PSR", float("inf")),
                float("inf"),
            )
            item["_ev_ebitda"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "EV / EBITDA", float("inf")),
                float("inf"),
            )

        items.sort(key=lambda x: x["_pl"])
        for rank, item in enumerate(items, 1):
            item["_rank_pl"] = rank

        items.sort(key=lambda x: x["_pvp"])
        for rank, item in enumerate(items, 1):
            item["_rank_pvp"] = rank

        items.sort(key=lambda x: x["_psr"])
        for rank, item in enumerate(items, 1):
            item["_rank_psr"] = rank

        items.sort(key=lambda x: x["_ev_ebitda"])
        for rank, item in enumerate(items, 1):
            item["_rank_ev_ebitda"] = rank

        for item in items:
            item["Rank Deep Value"] = item["_rank_pl"] + item["_rank_pvp"] + item["_rank_psr"] + item["_rank_ev_ebitda"]
            del item["_pl"]
            del item["_pvp"]
            del item["_psr"]
            del item["_ev_ebitda"]
            del item["_rank_pl"]
            del item["_rank_pvp"]
            del item["_rank_psr"]
            del item["_rank_ev_ebitda"]

        items.sort(key=lambda x: x["Rank Deep Value"])
        return items


class NetNetPipeline(ScreeningPipeline):
    """Benjamin Graham's Net-Net: stocks trading below NCAV per share, ranked by discount."""

    output_path = "data/strategies/netnet.json"
    strategy_name = "Net-Net (NCAV)"
    strategy_description = "Busca ações negociando abaixo do valor líquido de ativos circulantes (NCAV)."
    strategy_methodology_summary = "Filtra empresas com NCAV positivo e preço abaixo do NCAV por ação."
    strategy_use_cases = [
        "Explorar oportunidades extremas de desconto patrimonial.",
        "Triagem defensiva em cenários de estresse.",
    ]
    strategy_caveats = [
        "Sinal raro no mercado atual; pode gerar poucos resultados.",
        "Liquidação teórica pode não se materializar na prática.",
    ]
    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            ativo_circ = self._as_number(
                self._get_nested(item, "Dados Balanço Patrimonial", "Ativo Circulante", 0),
                0.0,
            )
            ativo = self._as_number(self._get_nested(item, "Dados Balanço Patrimonial", "Ativo", 0), 0.0)
            patrim_liq = self._as_number(
                self._get_nested(item, "Dados Balanço Patrimonial", "Patrim. Líq", 0),
                0.0,
            )
            nro_acoes = self._as_number(item.get("Nro. Ações", 0), 0.0)

            if ativo_circ <= 0 or ativo <= 0 or patrim_liq <= 0 or nro_acoes <= 0:
                continue

            ncav = ativo_circ - (ativo - patrim_liq)
            if ncav <= 0:
                continue

            ncav_per_share = ncav / nro_acoes
            cotacao = self._as_number(item.get("Cotação", float("inf")), float("inf"))
            if cotacao is None or cotacao >= ncav_per_share:
                continue

            item["NCAV per Share"] = round(ncav_per_share, 2)
            item["NCAV Discount"] = round((ncav_per_share - cotacao) / ncav_per_share, 4)
            result.append(item)

        return result

    def rank(self, items):
        items.sort(key=lambda x: x["NCAV Discount"], reverse=True)
        return items


class GARPPipeline(ScreeningPipeline):
    """Growth at a Reasonable Price: ranks by PEG ratio (lower is better)."""

    output_path = "data/strategies/garp.json"
    strategy_name = "GARP"
    strategy_description = "Combina preço e crescimento via PEG ratio (menor melhor)."
    strategy_methodology_summary = "Calcula PEG usando P/L e crescimento de receita 5 anos e ordena crescente."
    strategy_use_cases = [
        "Buscar crescimento com valuation ainda razoável.",
        "Evitar pagar caro demais por crescimento isolado.",
    ]
    strategy_caveats = [
        "Crescimento passado pode não se repetir.",
        "PEG depende fortemente da qualidade da estimativa de crescimento.",
    ]

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            pl = self._as_number(self._get_nested(item, "Indicadores fundamentalistas", "P/L", 0), 0.0)
            growth = self._as_number(self._get_nested(item, "Oscilações", "Cres. Rec (5a)", 0), 0.0)

            if pl <= 0 or growth <= 0:
                continue

            peg = pl / (growth * 100)
            if math.isinf(peg):
                continue

            item["PEG Ratio"] = round(peg, 4)
            result.append(item)

        return result

    def rank(self, items):
        items.sort(key=lambda x: x["PEG Ratio"])
        for rank, item in enumerate(items, 1):
            item["Rank GARP"] = rank
        return items


class MomentumValuePipeline(ScreeningPipeline):
    """Combines 12-month price momentum (higher=better) with P/VP (lower=better), 50/50."""

    output_path = "data/strategies/momentum_value.json"
    strategy_name = "Momentum + Value"
    strategy_description = "Combina força de preço de 12 meses com valuation por P/VP."
    strategy_methodology_summary = "Soma rank de momentum (maior melhor) com rank de P/VP (menor melhor)."
    strategy_use_cases = [
        "Misturar tendência de preço com disciplina de valuation.",
        "Evitar ações baratas sem confirmação de fluxo.",
    ]
    strategy_caveats = [
        "Momentum pode reverter rapidamente em mudanças de regime.",
        "P/VP é menos informativo para certos modelos de negócio.",
    ]

    def filter(self, items):
        base = super().filter(items)
        return [
            item for item in base
            if self._get_nested(item, "Oscilações", "12 meses", None) is not None
            and self._as_number(self._get_nested(item, "Indicadores fundamentalistas", "P/VP", 0), 0.0) > 0
        ]

    def rank(self, items):
        for item in items:
            item["_momentum"] = self._as_number(self._get_nested(item, "Oscilações", "12 meses", 0), 0.0)
            item["_pvp"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "P/VP", float("inf")),
                float("inf"),
            )

        items.sort(key=lambda x: x["_momentum"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Momentum"] = rank

        items.sort(key=lambda x: x["_pvp"])
        for rank, item in enumerate(items, 1):
            item["Rank P/VP"] = rank

        for item in items:
            item["Rank Momentum+Value"] = item["Rank Momentum"] + item["Rank P/VP"]
            del item["_momentum"]
            del item["_pvp"]

        items.sort(key=lambda x: x["Rank Momentum+Value"])
        return items


class ContrarianPipeline(ScreeningPipeline):
    """Contrarian: stocks near 52-week low with strong ROIC and low debt, ranked by proximity to low."""

    output_path = "data/strategies/contrarian.json"
    strategy_name = "Contrarian 52W"
    strategy_description = "Procura ações próximas da mínima de 52 semanas com fundamentos mínimos preservados."
    strategy_methodology_summary = (
        "Filtra proximidade da mínima, ROIC mínimo e dívida controlada; ordena por proximidade."
    )
    strategy_use_cases = [
        "Mapear possíveis reversões com filtro fundamental.",
        "Encontrar oportunidades fora do consenso recente.",
    ]
    strategy_caveats = [
        "Quedas podem continuar apesar de filtros fundamentais.",
        "Pode concentrar exposição em setores pressionados.",
    ]
    MAX_ABOVE_52W_LOW = 0.20
    MIN_ROIC = 0.10
    MAX_DEBT_RATIO = 1.5

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            cotacao = self._as_number(item.get("Cotação", None), float("nan"))
            min52 = self._as_number(item.get("Min 52 sem", None), float("nan"))
            roic = self._as_number(self._get_nested(item, "Oscilações", "ROIC", 0), 0.0)
            debt = self._as_number(
                self._get_nested(item, "Oscilações", "Div Br/ Patrim", float("inf")),
                float("inf"),
            )

            if math.isnan(cotacao) or math.isnan(min52) or min52 <= 0:
                continue

            above_low = (cotacao - min52) / min52
            if above_low > self.MAX_ABOVE_52W_LOW:
                continue
            if roic < self.MIN_ROIC:
                continue
            if debt > self.MAX_DEBT_RATIO:
                continue

            item["Above 52w Low"] = round(above_low, 4)
            result.append(item)

        return result

    def rank(self, items):
        items.sort(key=lambda x: x["Above 52w Low"])
        for rank, item in enumerate(items, 1):
            item["Rank Contrarian"] = rank
        return items


class CashRichPipeline(ScreeningPipeline):
    """Cash-rich stocks: ranked by Cash / Market Cap ratio (higher is better)."""

    output_path = "data/strategies/cashrich.json"
    strategy_name = "Cash-Rich"
    strategy_description = "Ranqueia empresas com maior caixa relativo ao valor de mercado."
    strategy_methodology_summary = "Calcula razão Caixa/Valor de Mercado e ordena de forma decrescente."
    strategy_use_cases = [
        "Identificar balanços defensivos com gordura de liquidez.",
        "Priorizar empresas com flexibilidade financeira.",
    ]
    strategy_caveats = [
        "Caixa alto pode sinalizar baixa alocação de capital.",
        "Não garante retorno ao acionista no curto prazo.",
    ]

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            cash = self._as_number(
                self._get_nested(item, "Dados Balanço Patrimonial", "Disponibilidades", 0),
                0.0,
            )
            market_cap = self._as_number(item.get("Valor de mercado", 0), 0.0)

            if cash <= 0 or market_cap <= 0:
                continue

            item["Cash / Market Cap"] = round(cash / market_cap, 4)
            result.append(item)

        return result

    def rank(self, items):
        items.sort(key=lambda x: x["Cash / Market Cap"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Cash-Rich"] = rank
        return items


class DuPontQualityPipeline(ScreeningPipeline):
    """DuPont ROE decomposition: rewards margin and efficiency, penalizes leverage."""

    output_path = "data/strategies/dupont.json"
    strategy_name = "DuPont Quality"
    strategy_description = "Decompõe ROE em margem, giro e alavancagem, priorizando qualidade sobre endividamento."
    strategy_methodology_summary = (
        "Soma ranks de Margem Líquida (maior melhor), Giro de Ativos (maior melhor) "
        "e Alavancagem (menor melhor)."
    )
    strategy_use_cases = [
        "Separar ROE genuíno de ROE inflado por dívida.",
        "Encontrar empresas com retornos sustentáveis.",
    ]
    strategy_caveats = [
        "Penaliza setores naturalmente alavancados (utilities, infraestrutura).",
        "Snapshot único não captura tendência da decomposição.",
    ]

    def rank(self, items):
        for item in items:
            item["_net_margin"] = self._as_number(
                self._get_nested(item, "Oscilações", "Marg. Líquida", float("-inf")), float("-inf")
            )
            item["_turnover"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "Giro Ativos", float("-inf")), float("-inf")
            )
            ativo = self._as_number(self._get_nested(item, "Dados Balanço Patrimonial", "Ativo", 0), 0.0)
            patrim = self._as_number(self._get_nested(item, "Dados Balanço Patrimonial", "Patrim. Líq", 0), 0.0)
            item["_leverage"] = ativo / patrim if patrim > 0 else float("inf")

        items.sort(key=lambda x: x["_net_margin"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Margin"] = rank

        items.sort(key=lambda x: x["_turnover"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Turnover"] = rank

        items.sort(key=lambda x: x["_leverage"])
        for rank, item in enumerate(items, 1):
            item["Rank Leverage"] = rank

        for item in items:
            item["Rank DuPont"] = item["Rank Margin"] + item["Rank Turnover"] + item["Rank Leverage"]
            item["Leverage"] = round(item["_leverage"], 2) if math.isfinite(item["_leverage"]) else None
            del item["_net_margin"]
            del item["_turnover"]
            del item["_leverage"]

        items.sort(key=lambda x: x["Rank DuPont"])
        return items


class SmallCapValuePipeline(ScreeningPipeline):
    """Small Cap Value: bottom quartile by market cap, ranked by EV/EBIT."""

    output_path = "data/strategies/smallcap_value.json"
    strategy_name = "Small Cap Value"
    strategy_description = "Filtra empresas do menor quartil de valor de mercado e ranqueia por EV/EBIT."
    strategy_methodology_summary = "Seleciona 25% menores por capitalização, depois ordena por EV/EBIT crescente."
    strategy_use_cases = [
        "Capturar prêmio de tamanho (size premium) com disciplina de valor.",
        "Explorar empresas negligenciadas por grandes fundos.",
    ]
    strategy_caveats = [
        "Small caps têm menor liquidez e maior volatilidade.",
        "Prêmio de tamanho é debatido e pode não persistir.",
    ]

    def filter(self, items):
        base = super().filter(items)
        if not base:
            return base

        market_caps = sorted(
            self._as_number(item.get("Valor de mercado", float("inf")), float("inf")) for item in base
        )
        quartile_cutoff = market_caps[len(market_caps) // 4] if market_caps else 0

        return [
            item for item in base
            if self._as_number(item.get("Valor de mercado", float("inf")), float("inf")) <= quartile_cutoff
        ]

    def rank(self, items):
        for item in items:
            item["_ev_ebit"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", float("inf")), float("inf")
            )

        items.sort(key=lambda x: x["_ev_ebit"])
        for rank, item in enumerate(items, 1):
            item["Rank Small Cap Value"] = rank
            del item["_ev_ebit"]

        return items


class LargeCapDividendPipeline(ScreeningPipeline):
    """Large Cap Dividend: top quartile by market cap, high yield, low debt."""

    output_path = "data/strategies/largecap_dividend.json"
    strategy_name = "Large Cap Dividend"
    strategy_description = "Seleciona blue chips com dividendo alto e dívida controlada."
    strategy_methodology_summary = (
        "Filtra 25% maiores por capitalização, Div. Yield >= 4%, Dív/Patrim <= 1, ordena por yield."
    )
    strategy_use_cases = [
        "Montar carteira de renda passiva com menor risco.",
        "Alternativa a renda fixa em cenários de juros baixos.",
    ]
    strategy_caveats = [
        "Yield alto pode refletir queda de preço, não generosidade.",
        "Dividendos passados não garantem pagamentos futuros.",
    ]
    MIN_DIV_YIELD = 0.04
    MAX_DEBT_RATIO = 1.0

    def filter(self, items):
        base = super().filter(items)
        if not base:
            return base

        market_caps = sorted(
            self._as_number(item.get("Valor de mercado", 0), 0.0) for item in base
        )
        quartile_cutoff = market_caps[3 * len(market_caps) // 4] if market_caps else float("inf")

        return [
            item for item in base
            if self._as_number(item.get("Valor de mercado", 0), 0.0) >= quartile_cutoff
            and self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "Div. Yield", 0), 0.0
            ) >= self.MIN_DIV_YIELD
            and self._as_number(
                self._get_nested(item, "Oscilações", "Div Br/ Patrim", float("inf")), float("inf")
            ) <= self.MAX_DEBT_RATIO
        ]

    def rank(self, items):
        for item in items:
            item["_div_yield"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "Div. Yield", 0), 0.0
            )

        items.sort(key=lambda x: x["_div_yield"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Large Cap Dividend"] = rank
            del item["_div_yield"]

        return items


class SectorRelativeValuePipeline(ScreeningPipeline):
    """Sector-Relative Value: cheapest quartile of each sector by EV/EBIT."""

    output_path = "data/strategies/sector_relative.json"
    strategy_name = "Sector-Relative Value"
    strategy_description = "Ranqueia ações contra seus pares de setor, não contra o mercado todo."
    strategy_methodology_summary = (
        "Agrupa por setor, ordena por EV/EBIT dentro de cada grupo, "
        "seleciona o quartil mais barato de cada setor."
    )
    strategy_use_cases = [
        "Encontrar ações baratas relativas ao setor, mesmo em setores 'caros'.",
        "Diversificar triagem entre setores ao invés de concentrar em poucos.",
    ]
    strategy_caveats = [
        "Setores com poucos representantes geram amostras frágeis.",
        "Não distingue subsetores com dinâmicas distintas.",
    ]

    def rank(self, items):
        sectors: dict[str, list[dict]] = {}
        for item in items:
            sector = self._get_sector(item) or "Unknown"
            sectors.setdefault(sector, []).append(item)

        ranked = []
        for sector, sector_items in sectors.items():
            if len(sector_items) < 4:
                continue

            for item in sector_items:
                item["_ev_ebit"] = self._as_number(
                    self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", float("inf")), float("inf")
                )

            sector_items.sort(key=lambda x: x["_ev_ebit"])
            quartile_size = len(sector_items) // 4 or 1

            for rank, item in enumerate(sector_items, 1):
                item["Sector"] = sector
                item["Sector Rank"] = rank
                item["Sector Size"] = len(sector_items)
                item["Sector Percentile"] = round(rank / len(sector_items), 4)
                del item["_ev_ebit"]

            ranked.extend(sector_items[:quartile_size])

        ranked.sort(key=lambda x: x["Sector Percentile"])
        for rank, item in enumerate(ranked, 1):
            item["Rank Sector-Relative"] = rank

        return ranked


class EarningsAccelerationPipeline(ScreeningPipeline):
    """Earnings Acceleration: annualized 3-month vs 12-month earnings trend."""

    output_path = "data/strategies/earnings_accel.json"
    strategy_name = "Earnings Acceleration"
    strategy_description = "Detecta empresas com lucro acelerando comparando trimestral anualizado vs 12 meses."
    strategy_methodology_summary = (
        "Calcula razão entre lucro trimestral anualizado (x4) e lucro 12 meses. "
        "Razão > 1 indica aceleração."
    )
    strategy_use_cases = [
        "Identificar turnarounds e empresas em melhora operacional.",
        "Antecipar revisões positivas de estimativas.",
    ]
    strategy_caveats = [
        "Um trimestre forte pode ser sazonal, não tendência.",
        "Comparação simples não ajusta por sazonalidade.",
    ]

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            demos = item.get("Dados demonstrativos de resultados", {})
            ultimos_12m = demos.get("Últimos 12 meses", {}) if isinstance(demos, dict) else {}
            ultimos_3m = demos.get("Últimos 3 meses", {}) if isinstance(demos, dict) else {}

            lucro_12m = self._as_number(ultimos_12m.get("Lucro Líquido", 0), 0.0)
            lucro_3m = self._as_number(ultimos_3m.get("Lucro Líquido", 0), 0.0)

            if lucro_12m > 0 and lucro_3m > 0:
                result.append(item)
        return result

    def rank(self, items):
        for item in items:
            demos = item.get("Dados demonstrativos de resultados", {})
            ultimos_12m = demos.get("Últimos 12 meses", {}) if isinstance(demos, dict) else {}
            ultimos_3m = demos.get("Últimos 3 meses", {}) if isinstance(demos, dict) else {}

            lucro_12m = self._as_number(ultimos_12m.get("Lucro Líquido", 1), 1.0)
            lucro_3m = self._as_number(ultimos_3m.get("Lucro Líquido", 0), 0.0)

            annualized_3m = lucro_3m * 4
            item["Earnings Acceleration"] = round(annualized_3m / lucro_12m, 4) if lucro_12m > 0 else 0

        items.sort(key=lambda x: x["Earnings Acceleration"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Earnings Accel"] = rank

        return items


class AssetLightQualityPipeline(ScreeningPipeline):
    """Asset-Light Quality: high ROIC + high asset turnover, low capital intensity."""

    output_path = "data/strategies/assetlight.json"
    strategy_name = "Asset-Light Quality"
    strategy_description = "Prioriza empresas com alto retorno e alto giro de ativos, que escalam sem capex pesado."
    strategy_methodology_summary = "Soma ranks de ROIC (maior melhor) e Giro de Ativos (maior melhor)."
    strategy_use_cases = [
        "Buscar modelos de negócio escaláveis com baixa intensidade de capital.",
        "Complementar triagens de valor com foco em eficiência operacional.",
    ]
    strategy_caveats = [
        "Setores asset-heavy (energia, mineração) serão sistematicamente desfavorecidos.",
        "Giro alto pode refletir margens comprimidas.",
    ]

    def rank(self, items):
        for item in items:
            item["_roic"] = self._as_number(
                self._get_nested(item, "Oscilações", "ROIC", float("-inf")), float("-inf")
            )
            item["_turnover"] = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "Giro Ativos", float("-inf")), float("-inf")
            )

        items.sort(key=lambda x: x["_roic"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank ROIC"] = rank

        items.sort(key=lambda x: x["_turnover"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Turnover"] = rank

        for item in items:
            item["Rank Asset-Light"] = item["Rank ROIC"] + item["Rank Turnover"]
            del item["_roic"]
            del item["_turnover"]

        items.sort(key=lambda x: x["Rank Asset-Light"])
        return items


class AltmanZScorePipeline(ScreeningPipeline):
    """Simplified Altman Z-Score: bankruptcy risk filter using 3 of 5 original components."""

    output_path = "data/strategies/altman.json"
    strategy_name = "Altman Z-Score"
    strategy_description = "Estima risco de falência usando versão simplificada do Z-Score de Altman."
    strategy_methodology_summary = (
        "Calcula Z = 3.3*(EBIT/Ativo) + 1.0*(Valor Mercado/Passivo Total) + 1.0*(Giro Ativos). "
        "Filtra Z >= 1.8."
    )
    strategy_use_cases = [
        "Filtrar empresas com alto risco de insolvência antes de investir.",
        "Usar como filtro de segurança complementar a outras triagens.",
    ]
    strategy_caveats = [
        "Versão simplificada com 3 dos 5 fatores originais (faltam capital de giro e lucros retidos).",
        "Modelo calibrado para mercados americanos; limiares podem diferir no Brasil.",
    ]
    MIN_Z_SCORE = 1.8

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            ativo = self._as_number(self._get_nested(item, "Dados Balanço Patrimonial", "Ativo", 0), 0.0)
            patrim = self._as_number(self._get_nested(item, "Dados Balanço Patrimonial", "Patrim. Líq", 0), 0.0)
            market_cap = self._as_number(item.get("Valor de mercado", 0), 0.0)

            if ativo <= 0 or patrim <= 0 or market_cap <= 0:
                continue

            total_liabilities = ativo - patrim
            if total_liabilities <= 0:
                continue

            result.append(item)
        return result

    def rank(self, items):
        for item in items:
            ebit_ativo = self._as_number(
                self._get_nested(item, "Oscilações", "EBIT / Ativo", 0), 0.0
            )
            giro_ativos = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "Giro Ativos", 0), 0.0
            )
            ativo = self._as_number(self._get_nested(item, "Dados Balanço Patrimonial", "Ativo", 1), 1.0)
            patrim = self._as_number(self._get_nested(item, "Dados Balanço Patrimonial", "Patrim. Líq", 0), 0.0)
            market_cap = self._as_number(item.get("Valor de mercado", 0), 0.0)

            total_liabilities = ativo - patrim
            x3 = ebit_ativo
            x4 = market_cap / total_liabilities if total_liabilities > 0 else 0
            x5 = giro_ativos

            item["Z-Score"] = round(3.3 * x3 + 1.0 * x4 + 1.0 * x5, 4)

        items = [item for item in items if item["Z-Score"] >= self.MIN_Z_SCORE]
        items.sort(key=lambda x: x["Z-Score"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Altman Z"] = rank

        return items


class BookValueDiscountPipeline(ScreeningPipeline):
    """Book Value Discount: stocks trading below book value (P/VP < 1)."""

    output_path = "data/strategies/bookvalue.json"
    strategy_name = "Book Value Discount"
    strategy_description = "Seleciona ações negociando abaixo do valor patrimonial (P/VP < 1)."
    strategy_methodology_summary = "Filtra P/VP entre 0 e 1, ordena pelo maior desconto sobre valor patrimonial."
    strategy_use_cases = [
        "Buscar ações com desconto patrimonial simples e direto.",
        "Complementar triagens de deep value com foco em balanço.",
    ]
    strategy_caveats = [
        "P/VP < 1 pode refletir destruição de valor, não oportunidade.",
        "Valor contábil pode divergir significativamente do valor econômico real.",
    ]

    def filter(self, items):
        base = super().filter(items)
        return [
            item for item in base
            if 0 < self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "P/VP", float("inf")), float("inf")
            ) < 1
        ]

    def rank(self, items):
        for item in items:
            pvp = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "P/VP", 1), 1.0
            )
            item["P/VP"] = pvp
            item["Book Value Discount"] = round(1 - pvp, 4)

        items.sort(key=lambda x: x["Book Value Discount"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Book Value"] = rank

        return items


class WorkingCapitalValuePipeline(ScreeningPipeline):
    """Working Capital Value: stocks cheap relative to working capital metrics."""

    output_path = "data/strategies/working_capital.json"
    strategy_name = "Working Capital Value"
    strategy_description = (
        "Seleciona ações baratas em relação ao capital de giro, "
        "usando P/Cap. Giro e P/Ativ Circ Líq como indicadores de subvalorização."
    )
    strategy_methodology_summary = (
        "Filtra P/Cap. Giro > 0 e P/Ativ Circ Liq > 0 (empresa com capital de giro positivo), "
        "pontua combinando os dois indicadores (quanto menor, melhor)."
    )
    strategy_use_cases = [
        "Identificar empresas subvalorizadas em relação ao capital de giro líquido.",
        "Complementar análises de deep value com foco em balanço operacional.",
    ]
    strategy_caveats = [
        "Empresas com capital de giro negativo são excluídas, incluindo muitas do setor financeiro.",
        "P/Cap. Giro baixo pode indicar negócio com ciclo operacional problemático.",
    ]

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            pcg = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "P/Cap. Giro", 0), 0
            )
            pacl = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "P/Ativ Circ Liq", 0), 0
            )
            if pcg > 0 and pacl > 0:
                result.append(item)
        return result

    def rank(self, items):
        for item in items:
            pcg = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "P/Cap. Giro", 0), 0
            )
            pacl = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "P/Ativ Circ Liq", 0), 0
            )
            item["P/Cap. Giro"] = pcg
            item["P/Ativ Circ Liq"] = pacl

        items.sort(key=lambda x: x["P/Cap. Giro"])
        for rank, item in enumerate(items, 1):
            item["Rank P/Cap. Giro"] = rank

        items.sort(key=lambda x: x["P/Ativ Circ Liq"])
        for rank, item in enumerate(items, 1):
            item["Rank P/Ativ Circ Liq"] = rank

        for item in items:
            item["WC Score"] = item["Rank P/Cap. Giro"] + item["Rank P/Ativ Circ Liq"]

        items.sort(key=lambda x: x["WC Score"])
        for rank, item in enumerate(items, 1):
            item["Rank Working Capital"] = rank

        return items


class MarginCompressionPipeline(ScreeningPipeline):
    """Margin Compression Detector: identifies stocks where EBIT margin is
    significantly lower than gross margin, suggesting potential for margin recovery."""

    output_path = "data/strategies/margin_compression.json"
    strategy_name = "Margin Compression Detector"
    strategy_description = (
        "Detecta empresas com gap significativo entre margem bruta e margem EBIT, "
        "sugerindo potencial de recuperação de margem operacional."
    )
    strategy_methodology_summary = (
        "Calcula o gap entre Marg. Bruta e Marg. EBIT. Empresas com gap grande "
        "têm despesas SGA/outros custos comprimindo a margem operacional, "
        "indicando potencial de melhoria caso custos sejam otimizados."
    )
    strategy_use_cases = [
        "Encontrar empresas com potencial de expansão de margem operacional.",
        "Identificar candidatas a reestruturação que podem melhorar rentabilidade.",
    ]
    strategy_caveats = [
        "Gap alto pode ser estrutural do setor, não necessariamente recuperável.",
        "Requer análise qualitativa dos componentes de custo para confirmar a tese.",
    ]

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            gross = self._as_number(self._get_nested(item, "Oscilações", "Marg. Bruta", 0), 0)
            ebit = self._as_number(self._get_nested(item, "Oscilações", "Marg. EBIT", 0), 0)
            if gross > 0 and ebit > 0 and gross > ebit:
                result.append(item)
        return result

    def rank(self, items):
        for item in items:
            gross = self._as_number(self._get_nested(item, "Oscilações", "Marg. Bruta", 0), 0)
            ebit = self._as_number(self._get_nested(item, "Oscilações", "Marg. EBIT", 0), 0)
            item["Marg. Bruta"] = gross
            item["Marg. EBIT"] = ebit
            item["Margin Gap"] = round(gross - ebit, 4) if gross > 0 else 0

        items.sort(key=lambda x: x["Margin Gap"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Margin Compression"] = rank

        return items


class FortressBalanceSheetPipeline(ScreeningPipeline):
    """Fortress Balance Sheet: companies with exceptionally strong balance sheets."""

    output_path = "data/strategies/fortress.json"
    strategy_name = "Fortress Balance Sheet"
    strategy_description = (
        "Seleciona empresas com balanço patrimonial excepcionalmente forte: "
        "alta liquidez corrente, baixo endividamento e EBIT positivo."
    )
    strategy_methodology_summary = (
        "Filtra Liquidez Corr > 1.5, Dív. Líq./Patrim. < 0.5, e EBIT positivo. "
        "Ordena por score composto de liquidez corrente e baixo endividamento."
    )
    strategy_use_cases = [
        "Buscar empresas resilientes em cenários de crise ou recessão.",
        "Construir carteira defensiva com baixo risco de solvência.",
    ]
    strategy_caveats = [
        "Balanço forte não garante crescimento ou boa alocação de capital.",
        "Excesso de caixa pode indicar falta de oportunidades de reinvestimento.",
    ]

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            liq_corr = self._as_number(self._get_nested(item, "Oscilações", "Liquidez Corr", 0), 0)
            div_patrim = self._as_number(
                self._get_nested(item, "Oscilações", "Div Br/ Patrim", float("inf")), float("inf")
            )
            if liq_corr > 1.5 and div_patrim < 0.5:
                result.append(item)
        return result

    def rank(self, items):
        for item in items:
            liq_corr = self._as_number(self._get_nested(item, "Oscilações", "Liquidez Corr", 0), 0)
            div_patrim = self._as_number(
                self._get_nested(item, "Oscilações", "Div Br/ Patrim", float("inf")), float("inf")
            )
            item["Liquidez Corr"] = liq_corr
            item["Div Br/ Patrim"] = div_patrim

        items.sort(key=lambda x: x["Liquidez Corr"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Liquidez"] = rank

        items.sort(key=lambda x: x["Div Br/ Patrim"])
        for rank, item in enumerate(items, 1):
            item["Rank Endividamento"] = rank

        for item in items:
            item["Fortress Score"] = item["Rank Liquidez"] + item["Rank Endividamento"]

        items.sort(key=lambda x: x["Fortress Score"])
        for rank, item in enumerate(items, 1):
            item["Rank Fortress"] = rank

        return items


class RedFlagPipeline(ScreeningPipeline):
    """Red Flag Detector: inverse screen that identifies stocks to AVOID."""

    output_path = "data/strategies/redflags.json"
    strategy_name = "Red Flag Detector"
    strategy_description = (
        "Triagem inversa que identifica ações com sinais de alerta: "
        "margens negativas, endividamento elevado, destruição de valor patrimonial."
    )
    strategy_methodology_summary = (
        "Conta red flags por empresa: Marg. EBIT negativa, Marg. Líquida negativa, "
        "Dív. Líq./Patrim. > 2, P/VP negativo, Liquidez Corr < 0.5, "
        "queda > 30% em 12 meses. Ordena pelo maior número de red flags."
    )
    strategy_use_cases = [
        "Identificar ações com alto risco para evitar em qualquer carteira.",
        "Usar como filtro negativo antes de selecionar ações de outras estratégias.",
    ]
    strategy_caveats = [
        "Red flags não significam necessariamente que a empresa vai falir — podem ser temporários.",
        "Alguns setores naturalmente apresentam métricas que disparam alertas (ex: utilities com alta dívida).",
    ]

    def filter(self, items):
        """Override: only filter by liquidity, we WANT to see problematic stocks."""
        return [
            item for item in items
            if self._get_liquidity(item) >= self.MIN_LIQUIDITY
            and self._get_sector(item) not in EXCLUDED_SECTORS
        ]

    def rank(self, items):
        for item in items:
            indicators = item.get("Indicadores fundamentalistas", {})
            if not isinstance(indicators, dict):
                indicators = {}

            flags = 0
            reasons = []

            ebit_margin = self._as_number(self._get_nested(item, "Oscilações", "Marg. EBIT", 0), 0)
            if ebit_margin < 0:
                flags += 1
                reasons.append("Marg. EBIT negativa")

            net_margin = self._as_number(self._get_nested(item, "Oscilações", "Marg. Líquida", 0), 0)
            if net_margin < 0:
                flags += 1
                reasons.append("Marg. Líquida negativa")

            div_patrim = self._as_number(self._get_nested(item, "Oscilações", "Div Br/ Patrim", 0), 0)
            if div_patrim > 2:
                flags += 1
                reasons.append("Div Br/ Patrim > 2")

            pvp = self._as_number(indicators.get("P/VP", 0), 0)
            if pvp < 0:
                flags += 1
                reasons.append("P/VP negativo")

            liq_corr = self._as_number(
                self._get_nested(item, "Oscilações", "Liquidez Corr", float("inf")), float("inf")
            )
            if liq_corr < 0.5:
                flags += 1
                reasons.append("Liquidez Corr < 0.5")

            change_12m = self._as_number(self._get_nested(item, "Oscilações", "12 meses", 0), 0)
            if change_12m < -0.30:
                flags += 1
                reasons.append("Queda > 30% em 12 meses")

            item["Red Flags"] = flags
            item["Red Flag Reasons"] = reasons

        items = [item for item in items if item["Red Flags"] >= 2]
        items.sort(key=lambda x: x["Red Flags"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Red Flags"] = rank

        return items


class EarningsYieldSpreadPipeline(ScreeningPipeline):
    """Earnings Yield Spread: EBIT/EV yield minus risk-free rate (Selic)."""

    output_path = "data/strategies/earnings_yield_spread.json"
    strategy_name = "Earnings Yield Spread"
    strategy_description = (
        "Calcula o spread entre o yield de lucro operacional (EBIT/EV) e a taxa Selic, "
        "identificando ações que oferecem prêmio sobre a renda fixa."
    )
    strategy_methodology_summary = (
        "Calcula Earnings Yield = 1/EV/EBIT. Subtrai a taxa Selic (padrão 14.25%). "
        "Ordena pelo maior spread positivo — ações com maior prêmio sobre a renda fixa."
    )
    strategy_use_cases = [
        "Comparar o retorno implícito de ações vs. renda fixa no cenário atual de juros.",
        "Identificar ações baratas mesmo em ambiente de Selic alta.",
    ]
    strategy_caveats = [
        "A taxa Selic padrão (14.25%) pode ficar desatualizada — ajustar conforme cenário.",
        "Earnings yield é baseado em EBIT passado, não projeções futuras.",
    ]

    SELIC_RATE = 0.1425

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            ev_ebit = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", 0), 0
            )
            if ev_ebit > 0:
                earnings_yield = 1.0 / ev_ebit
                if earnings_yield > self.SELIC_RATE:
                    result.append(item)
        return result

    def rank(self, items):
        for item in items:
            ev_ebit = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", 0), 0
            )
            earnings_yield = 1.0 / ev_ebit if ev_ebit > 0 else 0
            spread = earnings_yield - self.SELIC_RATE
            item["Earnings Yield"] = round(earnings_yield, 4)
            item["Selic Rate"] = self.SELIC_RATE
            item["EY Spread"] = round(spread, 4)

        items.sort(key=lambda x: x["EY Spread"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank EY Spread"] = rank

        return items


class BuffettCompositePipeline(ScreeningPipeline):
    """Buffett Composite: ROE > 15%, low debt, consistent margins, reasonable P/L."""

    output_path = "data/strategies/buffett.json"
    strategy_name = "Buffett Composite"
    strategy_description = (
        "Aplica critérios inspirados em Warren Buffett: ROE elevado (>15%), "
        "endividamento controlado, margens consistentes e P/L razoável."
    )
    strategy_methodology_summary = (
        "Filtra ROE > 15%, Dív. Líq./Patrim. < 1, Marg. Líquida > 10%, "
        "P/L entre 0 e 25. Ordena por score composto de ROE e margem líquida."
    )
    strategy_use_cases = [
        "Buscar empresas com vantagem competitiva duradoura (economic moat).",
        "Construir carteira de longo prazo com foco em qualidade e preço justo.",
    ]
    strategy_caveats = [
        "ROE alto com alavancagem alta pode ser artificialmente inflado.",
        "Critérios qualitativos de Buffett (gestão, marca, moat) não são capturados por dados quantitativos.",
    ]

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            indicators = item.get("Indicadores fundamentalistas", {})
            if not isinstance(indicators, dict):
                continue
            roe = self._as_number(self._get_nested(item, "Oscilações", "ROE", 0), 0)
            div_patrim = self._as_number(
                self._get_nested(item, "Oscilações", "Div Br/ Patrim", float("inf")), float("inf")
            )
            marg_liq = self._as_number(self._get_nested(item, "Oscilações", "Marg. Líquida", 0), 0)
            pl = self._as_number(indicators.get("P/L", 0), 0)

            if roe > 0.15 and div_patrim < 1 and marg_liq > 0.10 and 0 < pl < 25:
                result.append(item)
        return result

    def rank(self, items):
        for item in items:
            roe = self._as_number(self._get_nested(item, "Oscilações", "ROE", 0), 0)
            marg_liq = self._as_number(self._get_nested(item, "Oscilações", "Marg. Líquida", 0), 0)
            item["ROE"] = roe
            item["Marg. Líquida"] = marg_liq

        items.sort(key=lambda x: x["ROE"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank ROE"] = rank

        items.sort(key=lambda x: x["Marg. Líquida"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Margem"] = rank

        for item in items:
            item["Buffett Score"] = item["Rank ROE"] + item["Rank Margem"]

        items.sort(key=lambda x: x["Buffett Score"])
        for rank, item in enumerate(items, 1):
            item["Rank Buffett"] = rank

        return items


class VolatilityAdjustedValuePipeline(ScreeningPipeline):
    """Volatility-Adjusted Value: EV/EBIT penalized by 52-week price range volatility."""

    output_path = "data/strategies/volatility_adjusted.json"
    strategy_name = "Volatility-Adjusted Value"
    strategy_description = (
        "Combina valuation (EV/EBIT) com penalidade por volatilidade baseada na "
        "amplitude de preço das últimas 52 semanas."
    )
    strategy_methodology_summary = (
        "Calcula volatilidade como (Max52sem - Min52sem) / Min52sem. "
        "Score = EV/EBIT x (1 + volatilidade). Quanto menor o score, melhor - "
        "ação barata com baixa oscilação de preço."
    )
    strategy_use_cases = [
        "Encontrar ações baratas e estáveis para investidores avessos a risco.",
        "Filtrar value traps que são baratas mas extremamente voláteis.",
    ]
    strategy_caveats = [
        "Volatilidade passada não prevê volatilidade futura.",
        "Amplitude 52 semanas é uma proxy simples — não substitui métricas como beta ou desvio padrão.",
    ]

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            ev_ebit = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", 0), 0
            )
            min_52 = self._as_number(item.get("Min 52 sem", 0), 0)
            max_52 = self._as_number(item.get("Max 52 sem", 0), 0)
            if ev_ebit > 0 and min_52 > 0 and max_52 > min_52:
                result.append(item)
        return result

    def rank(self, items):
        for item in items:
            ev_ebit = self._as_number(
                self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", 0), 0
            )
            min_52 = self._as_number(item.get("Min 52 sem", 0), 0)
            max_52 = self._as_number(item.get("Max 52 sem", 0), 0)
            volatility = (max_52 - min_52) / min_52 if min_52 > 0 else 0
            score = ev_ebit * (1 + volatility)
            item["EV/EBIT"] = ev_ebit
            item["52w Volatility"] = round(volatility, 4)
            item["VA Score"] = round(score, 4)

        items.sort(key=lambda x: x["VA Score"])
        for rank, item in enumerate(items, 1):
            item["Rank Vol-Adjusted"] = rank

        return items


class ConsensusScreenPipeline(ScreeningPipeline):
    """Consensus Screen: stocks that appear in multiple other strategy outputs."""

    output_path = "data/strategies/consensus.json"
    strategy_name = "Consensus Screen"
    strategy_description = (
        "Meta-estratégia que identifica ações presentes em múltiplas outras estratégias, "
        "sinalizando consenso entre diferentes metodologias de seleção."
    )
    strategy_methodology_summary = (
        "Lê os arquivos JSON de saída das demais estratégias e conta em quantas "
        "cada ação aparece. Filtra ações presentes em pelo menos 5 estratégias."
    )
    strategy_use_cases = [
        "Construir carteira de alta convicção com validação cruzada entre métodos.",
        "Reduzir risco de viés metodológico ao exigir consenso entre estratégias diversas.",
    ]
    strategy_caveats = [
        "Estratégias com filtros parecidos podem gerar falsa impressão de consenso.",
        "Depende da execução prévia de todas as outras estratégias na mesma sessão.",
    ]

    MIN_APPEARANCES = 5

    def rank(self, items):
        import json
        from pathlib import Path

        strategies_dir = Path("data/strategies")
        own_path = Path(self.output_path)

        appearances: dict[str, int] = {}
        strategy_count = 0

        if strategies_dir.exists():
            for json_file in sorted(strategies_dir.glob("*.json")):
                if json_file == own_path:
                    continue
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    stocks = data.get("stocks", [])
                    strategy_count += 1
                    for stock in stocks:
                        ticker = stock.get("Papel", "")
                        if ticker:
                            appearances[ticker] = appearances.get(ticker, 0) + 1
                except (json.JSONDecodeError, OSError):
                    continue

        ticker_set = {ticker for ticker, count in appearances.items() if count >= self.MIN_APPEARANCES}

        result = []
        for item in items:
            ticker = item.get("Papel", "")
            if ticker in ticker_set:
                item["Appearances"] = appearances.get(ticker, 0)
                item["Strategy Count"] = strategy_count
                result.append(item)

        result.sort(key=lambda x: x["Appearances"], reverse=True)
        for rank, item in enumerate(result, 1):
            item["Rank Consensus"] = rank

        return result
