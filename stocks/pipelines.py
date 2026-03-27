import datetime as dt
import json
import logging
import math
import re

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


EXCLUDED_SECTORS = [
    "Financeiros",
    "Holdings Diversificadas",
    "Previdência e Seguros",
    "Serviços Financeiros Diversos",
]


class ScreeningPipeline:
    """Base class for stock screening pipelines.

    Collects all items during the crawl, then filters and ranks on spider close.
    Subclasses implement `rank` to define their ranking strategy.
    """

    MIN_LIQUIDITY = 150_000
    TOP_N = 30
    output_path: str
    strategy_name: str | None = None
    strategy_description: str | None = None
    strategy_methodology_summary: str | None = None
    strategy_use_cases: list[str] | None = None
    strategy_caveats: list[str] | None = None

    def __init__(self):
        self.items = []

    @staticmethod
    def _as_number(value, default=0.0):
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip().replace(".", "").replace(",", ".")
            if not cleaned or cleaned == "-":
                return default
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
        return self._get_nested(item, "Dados gerais", "Setor", None)

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
        return {
            "strategy_id": self._strategy_id(),
            "name": self._strategy_name(),
            "description": self._strategy_description(),
            "methodology_summary": self._strategy_methodology_summary(),
            "use_cases": self._strategy_use_cases(),
            "caveats": self._strategy_caveats(),
            "generated_at": dt.datetime.now(dt.UTC).isoformat(),
            "universe_size": len(universe),
            "filtered_size": len(filtered),
            "result_size": len(ranked),
            "stocks": ranked,
        }

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        if not self.items:
            return

        filtered = self.filter(self.items)
        logger.info("%s: %d -> %d items after filtering",
                    self.__class__.__name__, len(self.items), len(filtered))

        ranked = self.rank(filtered)[:self.TOP_N]
        payload = self._build_output_payload(self.items, filtered, ranked)

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)

        logger.info("%s: top %d written to %s",
                    self.__class__.__name__, len(ranked), self.output_path)


class MagicFormulaPipeline(ScreeningPipeline):
    """Magic Formula (Joel Greenblatt): ranks by combined EV/EBIT + ROIC."""

    output_path = "magicformula.json"
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
            item["_ev_ebit"] = self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", float("inf"))
            item["_roic"] = self._get_nested(item, "Oscilações", "ROIC", float("-inf"))

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

    output_path = "cdv.json"
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
            item["_ev_ebit"] = self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", float("inf"))

        items.sort(key=lambda x: x["_ev_ebit"])
        for rank, item in enumerate(items, 1):
            item["Rank EV / EBIT"] = rank

        for item in items:
            del item["_ev_ebit"]

        return items


class IntersectionPipeline(ScreeningPipeline):
    """Finds stocks present in both Magic Formula and CDV top-N portfolios.

    Reuses the same base filtering/collection, then intersects both ranking strategies.
    """

    output_path = "intersection.json"
    strategy_name = "Interseção Magic Formula + CDV"
    strategy_description = "Mostra apenas ações que aparecem simultaneamente no top da Magic Formula e CDV."
    strategy_methodology_summary = "Calcula o top N de cada estratégia e retorna apenas o conjunto em comum."
    strategy_use_cases = [
        "Encontrar consenso entre duas abordagens de valor.",
        "Reduzir universo para estudos aprofundados.",
    ]
    strategy_caveats = [
        "Interseções podem ficar pequenas em mercados esticados.",
        "Consenso entre estratégias não elimina risco fundamental.",
    ]

    def rank(self, items):
        # Rank with both strategies to find top N of each
        magic = MagicFormulaPipeline()
        cdv = CDVPipeline()

        magic_ranked = magic.rank([dict(item) for item in items])[:self.TOP_N]
        cdv_ranked = cdv.rank([dict(item) for item in items])[:self.TOP_N]

        magic_stocks = {item["Papel"] for item in magic_ranked}
        intersection = [item for item in cdv_ranked if item["Papel"] in magic_stocks]
        return intersection

    def close_spider(self, spider):
        if not self.items:
            return

        filtered = self.filter(self.items)
        logger.info("IntersectionPipeline: %d -> %d items after filtering",
                     len(self.items), len(filtered))

        intersection = self.rank(filtered)
        payload = self._build_output_payload(self.items, filtered, intersection)

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)

        logger.info("IntersectionPipeline: %d stocks in both portfolios, written to %s",
                     len(intersection), self.output_path)


class GrahamNumberPipeline(ScreeningPipeline):
    """Benjamin Graham: ranks by discount to Graham Number.

    Graham Number = sqrt(22.5 * LPA * VPA). Stocks trading below this
    intrinsic value estimate are considered undervalued. Ranked by the
    margin of safety (discount percentage).
    """

    output_path = "graham.json"
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
            if (self._get_nested(item, "Oscilações", "LPA", 0) or 0) > 0
            and (self._get_nested(item, "Oscilações", "VPA", 0) or 0) > 0
        ]

    def rank(self, items):
        for item in items:
            lpa = self._get_nested(item, "Oscilações", "LPA", 0)
            vpa = self._get_nested(item, "Oscilações", "VPA", 0)
            graham_number = math.sqrt(22.5 * lpa * vpa)
            cotacao = item.get("Cotação", float("inf"))
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

    output_path = "bazin.json"
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
            if (self._get_nested(item, "Indicadores fundamentalistas", "Div. Yield", 0) or 0) >= self.MIN_DIV_YIELD
            and (self._get_nested(item, "Oscilações", "Div Br/ Patrim", float("inf")) or 0) <= self.MAX_DEBT_RATIO
        ]

    def rank(self, items):
        for item in items:
            item["_div_yield"] = self._get_nested(item, "Indicadores fundamentalistas", "Div. Yield", 0) or 0

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

    output_path = "quality.json"
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
            item["_roic"] = self._get_nested(item, "Oscilações", "ROIC", float("-inf")) or 0
            item["_net_margin"] = self._get_nested(item, "Oscilações", "Marg. Líquida", float("-inf")) or 0

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

    output_path = "piotroski.json"
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
        roe = self._get_nested(item, "Oscilações", "ROE", 0) or 0
        roic = self._get_nested(item, "Oscilações", "ROIC", 0) or 0
        ebit_ativo = self._get_nested(item, "Oscilações", "EBIT / Ativo", 0) or 0

        if roe > 0:
            score += 1  # Positive ROE
        if roic > 0:
            score += 1  # Positive ROIC (proxy for positive operating cash flow)
        if ebit_ativo > 0:
            score += 1  # Positive return on assets

        # Leverage / liquidity signals
        liq_corr = self._get_nested(item, "Oscilações", "Liquidez Corr", 0) or 0
        div_br_patrim = self._get_nested(item, "Oscilações", "Div Br/ Patrim", float("inf")) or 0

        if liq_corr > 1:
            score += 1  # Current ratio > 1
        if div_br_patrim < 1:
            score += 1  # Low debt-to-equity

        # Efficiency signals
        marg_bruta = self._get_nested(item, "Oscilações", "Marg. Bruta", 0) or 0
        marg_ebit = self._get_nested(item, "Oscilações", "Marg. EBIT", 0) or 0
        giro_ativos = self._get_nested(item, "Indicadores fundamentalistas", "Giro Ativos", 0) or 0
        cresc_rec = self._get_nested(item, "Oscilações", "Cres. Rec (5a)", 0) or 0

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

    output_path = "multifactor.json"
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
            item["_ev_ebit"] = self._get_nested(item, "Indicadores fundamentalistas", "EV / EBIT", float("inf"))
            item["_roic"] = self._get_nested(item, "Oscilações", "ROIC", float("-inf")) or 0
            item["_growth"] = self._get_nested(item, "Oscilações", "Cres. Rec (5a)", float("-inf")) or 0
            item["_div_yield"] = self._get_nested(item, "Indicadores fundamentalistas", "Div. Yield", 0) or 0

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

    output_path = "acquirers.json"
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
            item["_ev_ebitda"] = self._get_nested(item, "Indicadores fundamentalistas", "EV / EBITDA", float("inf"))

        items.sort(key=lambda x: x["_ev_ebitda"])
        for rank, item in enumerate(items, 1):
            item["Rank Acquirer's Multiple"] = rank
            del item["_ev_ebitda"]

        return items


class DeepValuePipeline(ScreeningPipeline):
    """Combined rank of P/L + P/VP + PSR + EV/EBITDA (equal weight). Lower combined rank is better."""

    output_path = "deepvalue.json"
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
            if (self._get_nested(item, "Indicadores fundamentalistas", "P/L", 0) or 0) > 0
        ]

    def rank(self, items):
        for item in items:
            item["_pl"] = self._get_nested(item, "Indicadores fundamentalistas", "P/L", float("inf"))
            item["_pvp"] = self._get_nested(item, "Indicadores fundamentalistas", "P/VP", float("inf"))
            item["_psr"] = self._get_nested(item, "Indicadores fundamentalistas", "PSR", float("inf"))
            item["_ev_ebitda"] = self._get_nested(item, "Indicadores fundamentalistas", "EV / EBITDA", float("inf"))

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

    output_path = "netnet.json"
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
    TOP_N = 100

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            ativo_circ = self._get_nested(item, "Dados Balanço Patrimonial", "Ativo Circulante", 0) or 0
            ativo = self._get_nested(item, "Dados Balanço Patrimonial", "Ativo", 0) or 0
            patrim_liq = self._get_nested(item, "Dados Balanço Patrimonial", "Patrim. Líq", 0) or 0
            nro_acoes = item.get("Nro. Ações", 0) or 0

            if ativo_circ <= 0 or ativo <= 0 or patrim_liq <= 0 or nro_acoes <= 0:
                continue

            ncav = ativo_circ - (ativo - patrim_liq)
            if ncav <= 0:
                continue

            ncav_per_share = ncav / nro_acoes
            cotacao = item.get("Cotação", float("inf"))
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

    output_path = "garp.json"
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

    output_path = "momentum_value.json"
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
            and (self._get_nested(item, "Indicadores fundamentalistas", "P/VP", 0) or 0) > 0
        ]

    def rank(self, items):
        for item in items:
            item["_momentum"] = self._get_nested(item, "Oscilações", "12 meses", 0)
            item["_pvp"] = self._get_nested(item, "Indicadores fundamentalistas", "P/VP", float("inf"))

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

    output_path = "contrarian.json"
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
            cotacao = item.get("Cotação", None)
            min52 = item.get("Min 52 sem", None)
            roic = self._as_number(self._get_nested(item, "Oscilações", "ROIC", 0), 0.0)
            debt = self._as_number(
                self._get_nested(item, "Oscilações", "Div Br/ Patrim", float("inf")),
                float("inf"),
            )

            if cotacao is None or min52 is None or min52 <= 0:
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

    output_path = "cashrich.json"
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
            cash = self._get_nested(item, "Dados Balanço Patrimonial", "Disponibilidades", 0) or 0
            market_cap = item.get("Valor de mercado", 0) or 0

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
