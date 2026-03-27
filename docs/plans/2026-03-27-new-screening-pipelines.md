# New Screening Pipelines Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 7 new stock screening pipelines (Acquirer's Multiple, Deep Value Composite, Net-Net/NCAV, GARP, Momentum+Value, 52-Week Low Contrarian, Cash-Rich) to the existing Scrapy pipeline architecture.

**Architecture:** Each pipeline subclasses `ScreeningPipeline` in `stocks/pipelines.py`, overriding `filter()` and/or `rank()`. They collect items via `process_item()` during the crawl and produce ranked JSON output on `close_spider()`. All are registered in the fundamentus spider's `custom_settings["ITEM_PIPELINES"]` at priority 700.

**Tech Stack:** Python, Scrapy pipelines, existing `ScreeningPipeline` base class in `stocks/pipelines.py`

---

## Available Data Fields Reference

These are the fields available on each stock item after pipeline processing. All new pipelines will use `self._get_nested(item, section, key, default)` for nested access and `item.get(key, default)` for top-level fields.

**Top-level:** `Papel`, `Cotação`, `Liq.2meses`, `Valor de mercado`, `Valor da firma`, `Min 52 sem`, `Max 52 sem`, `Nro. Ações`, `Setor`, `Subsetor`, `Tipo`, `Empresa`

**Oscilações:** `LPA`, `VPA`, `Marg. Bruta`, `Marg. EBIT`, `Marg. Líquida`, `EBIT / Ativo`, `ROIC`, `ROE`, `Liquidez Corr`, `Div Br/ Patrim`, `Cres. Rec (5a)`, `Dia`, `Mês`, `30 dias`, `12 meses` (price oscillations)

**Indicadores fundamentalistas:** `P/L`, `P/VP`, `P/EBIT`, `PSR`, `P/Ativos`, `P/Cap. Giro`, `P/Ativ Circ Liq`, `Div. Yield`, `EV / EBITDA`, `EV / EBIT`, `Giro Ativos`

**Dados Balanço Patrimonial:** `Ativo`, `Dív. Bruta`, `Disponibilidades`, `Dív. Líquida`, `Ativo Circulante`, `Patrim. Líq`

**Dados demonstrativos de resultados > Últimos 12 meses / Últimos 3 meses:** `Receita Líquida`, `EBIT`, `Lucro Líquido`

---

### Task 1: AcquirersMultiplePipeline

**Files:**
- Modify: `stocks/pipelines.py` (append after `MultiFactorPipeline` class, ~line 460)
- Modify: `stocks/spiders/fundamentus.py:28-41` (add to `ITEM_PIPELINES`)
- Modify: `.gitignore:71-80` (add `acquirers.json`)

**Description:** Tobias Carlisle's Acquirer's Multiple. Ranks purely by EV/EBITDA (lower is better). Similar to CDV but uses EBITDA instead of EBIT, which is less affected by depreciation differences across industries.

**Step 1: Add pipeline class to `stocks/pipelines.py`**

Append after the `MultiFactorPipeline` class:

```python
class AcquirersMultiplePipeline(ScreeningPipeline):
    """Acquirer's Multiple (Tobias Carlisle): ranks by EV/EBITDA only.

    Uses enterprise value over EBITDA instead of EBIT, making it less
    sensitive to depreciation differences across industries.
    """

    output_path = "acquirers.json"

    def rank(self, items):
        for item in items:
            item["_ev_ebitda"] = self._get_nested(
                item, "Indicadores fundamentalistas", "EV / EBITDA", float("inf")
            )

        items.sort(key=lambda x: x["_ev_ebitda"])
        for rank, item in enumerate(items, 1):
            item["Rank Acquirer's Multiple"] = rank

        for item in items:
            del item["_ev_ebitda"]

        return items
```

**Step 2: Register in spider**

Add to `ITEM_PIPELINES` dict in `stocks/spiders/fundamentus.py`:
```python
"stocks.pipelines.AcquirersMultiplePipeline": 700,
```

**Step 3: Add to `.gitignore`**

Add `acquirers.json` to the generated data section.

**Step 4: Run checks**

```bash
just check
```
Expected: All checks passed.

**Step 5: Commit**

```bash
git add stocks/pipelines.py stocks/spiders/fundamentus.py .gitignore
git commit -m "feat: add Acquirer's Multiple pipeline (EV/EBITDA ranking)"
```

---

### Task 2: DeepValuePipeline

**Files:**
- Modify: `stocks/pipelines.py` (append after `AcquirersMultiplePipeline`)
- Modify: `stocks/spiders/fundamentus.py:28-41`
- Modify: `.gitignore`

**Description:** Combined rank of P/L + P/VP + PSR + EV/EBITDA. Catches stocks that are cheap across multiple valuation metrics, not just one. Each factor is ranked independently and summed (equal weight).

**Step 1: Add pipeline class to `stocks/pipelines.py`**

```python
class DeepValuePipeline(ScreeningPipeline):
    """Deep Value Composite: combined rank of P/L, P/VP, PSR, and EV/EBITDA.

    Stocks must be cheap across multiple valuation lenses. Each metric
    is ranked independently and summed with equal weight.
    """

    output_path = "deepvalue.json"

    def filter(self, items):
        """Base filter plus require positive P/L (profitable companies only)."""
        base = super().filter(items)
        return [
            item for item in base
            if (self._get_nested(item, "Indicadores fundamentalistas", "P/L", 0) or 0) > 0
        ]

    def rank(self, items):
        factors = {
            "P/L": ("Indicadores fundamentalistas", "P/L", float("inf"), False),
            "P/VP": ("Indicadores fundamentalistas", "P/VP", float("inf"), False),
            "PSR": ("Indicadores fundamentalistas", "PSR", float("inf"), False),
            "EV / EBITDA": ("Indicadores fundamentalistas", "EV / EBITDA", float("inf"), False),
        }

        for key, (section, field, default, _reverse) in factors.items():
            for item in items:
                item[f"_{key}"] = self._get_nested(item, section, field, default) or default

            items.sort(key=lambda x, k=f"_{key}": x[k])
            for rank, item in enumerate(items, 1):
                item[f"Rank {key}"] = rank

        for item in items:
            item["Rank Deep Value"] = sum(item[f"Rank {key}"] for key in factors)
            for key in factors:
                del item[f"_{key}"]

        items.sort(key=lambda x: x["Rank Deep Value"])
        return items
```

**Step 2: Register in spider**

Add to `ITEM_PIPELINES`:
```python
"stocks.pipelines.DeepValuePipeline": 700,
```

**Step 3: Add `deepvalue.json` to `.gitignore`**

**Step 4: Run checks**

```bash
just check
```

**Step 5: Commit**

```bash
git add stocks/pipelines.py stocks/spiders/fundamentus.py .gitignore
git commit -m "feat: add Deep Value Composite pipeline (P/L + P/VP + PSR + EV/EBITDA)"
```

---

### Task 3: NetNetPipeline

**Files:**
- Modify: `stocks/pipelines.py`
- Modify: `stocks/spiders/fundamentus.py:28-41`
- Modify: `.gitignore`

**Description:** Benjamin Graham's Net-Net / NCAV strategy. NCAV = Ativo Circulante - Total Liabilities (where Total Liabilities = Ativo - Patrim. Líq). Stocks trading below NCAV per share are trading below liquidation value. Ranked by discount to NCAV. Will likely produce few results in modern Brazilian markets.

**Step 1: Add pipeline class to `stocks/pipelines.py`**

```python
class NetNetPipeline(ScreeningPipeline):
    """Net-Net / NCAV (Benjamin Graham): stocks trading below liquidation value.

    NCAV = Current Assets - Total Liabilities. Stocks trading below
    NCAV per share are priced below what they'd be worth if liquidated.
    Ranked by discount to NCAV. Produces few results in modern markets.
    """

    output_path = "netnet.json"
    TOP_N = 100  # Relaxed since very few stocks qualify

    def filter(self, items):
        """Base filter plus require NCAV data and positive NCAV."""
        base = super().filter(items)
        result = []
        for item in base:
            ativo_circ = self._get_nested(item, "Dados Balanço Patrimonial", "Ativo Circulante", 0) or 0
            ativo = self._get_nested(item, "Dados Balanço Patrimonial", "Ativo", 0) or 0
            patrim_liq = self._get_nested(item, "Dados Balanço Patrimonial", "Patrim. Líq", 0) or 0
            nro_acoes = item.get("Nro. Ações", 0) or 0

            if ativo_circ > 0 and ativo > 0 and patrim_liq > 0 and nro_acoes > 0:
                total_liabilities = ativo - patrim_liq
                ncav = ativo_circ - total_liabilities
                if ncav > 0:
                    result.append(item)
        return result

    def rank(self, items):
        for item in items:
            ativo_circ = self._get_nested(item, "Dados Balanço Patrimonial", "Ativo Circulante", 0)
            ativo = self._get_nested(item, "Dados Balanço Patrimonial", "Ativo", 0)
            patrim_liq = self._get_nested(item, "Dados Balanço Patrimonial", "Patrim. Líq", 0)
            nro_acoes = item.get("Nro. Ações", 1)

            total_liabilities = ativo - patrim_liq
            ncav = ativo_circ - total_liabilities
            ncav_per_share = ncav / nro_acoes

            cotacao = item.get("Cotação", float("inf"))
            item["NCAV per Share"] = round(ncav_per_share, 2)
            item["NCAV Discount"] = round((ncav_per_share - cotacao) / ncav_per_share, 4) if ncav_per_share > 0 else 0

        # Only keep stocks trading below NCAV per share
        items = [item for item in items if item.get("Cotação", float("inf")) < item["NCAV per Share"]]
        items.sort(key=lambda x: x["NCAV Discount"], reverse=True)
        return items
```

**Step 2: Register in spider**

Add to `ITEM_PIPELINES`:
```python
"stocks.pipelines.NetNetPipeline": 700,
```

**Step 3: Add `netnet.json` to `.gitignore`**

**Step 4: Run checks**

```bash
just check
```

**Step 5: Commit**

```bash
git add stocks/pipelines.py stocks/spiders/fundamentus.py .gitignore
git commit -m "feat: add Net-Net/NCAV pipeline (liquidation value screening)"
```

---

### Task 4: GARPPipeline

**Files:**
- Modify: `stocks/pipelines.py`
- Modify: `stocks/spiders/fundamentus.py:28-41`
- Modify: `.gitignore`

**Description:** Growth at a Reasonable Price. Uses a PEG-like ratio: P/L divided by 5-year revenue growth rate (Cres. Rec 5a expressed as percentage). Filters for positive P/L and positive growth. Lower PEG = better value for the growth you're getting.

**Step 1: Add pipeline class to `stocks/pipelines.py`**

```python
class GARPPipeline(ScreeningPipeline):
    """GARP (Growth at a Reasonable Price): PEG-like ratio using P/L and 5y growth.

    PEG = P/L / (5-year revenue growth * 100). Lower PEG means you're
    paying less for each unit of growth. Filters for profitable,
    growing companies.
    """

    output_path = "garp.json"

    def filter(self, items):
        """Base filter plus require positive P/L and positive 5y growth."""
        base = super().filter(items)
        return [
            item for item in base
            if (self._get_nested(item, "Indicadores fundamentalistas", "P/L", 0) or 0) > 0
            and (self._get_nested(item, "Oscilações", "Cres. Rec (5a)", 0) or 0) > 0
        ]

    def rank(self, items):
        for item in items:
            pl = self._get_nested(item, "Indicadores fundamentalistas", "P/L", float("inf"))
            growth = self._get_nested(item, "Oscilações", "Cres. Rec (5a)", 0.001)
            growth_pct = growth * 100  # Convert decimal to percentage for PEG
            item["PEG Ratio"] = round(pl / growth_pct, 4) if growth_pct > 0 else float("inf")

        items = [item for item in items if item["PEG Ratio"] < float("inf")]
        items.sort(key=lambda x: x["PEG Ratio"])
        for rank, item in enumerate(items, 1):
            item["Rank GARP"] = rank

        return items
```

**Step 2: Register in spider**

Add to `ITEM_PIPELINES`:
```python
"stocks.pipelines.GARPPipeline": 700,
```

**Step 3: Add `garp.json` to `.gitignore`**

**Step 4: Run checks**

```bash
just check
```

**Step 5: Commit**

```bash
git add stocks/pipelines.py stocks/spiders/fundamentus.py .gitignore
git commit -m "feat: add GARP pipeline (PEG ratio growth/value screening)"
```

---

### Task 5: MomentumValuePipeline

**Files:**
- Modify: `stocks/pipelines.py`
- Modify: `stocks/spiders/fundamentus.py:28-41`
- Modify: `.gitignore`

**Description:** Combines 12-month price momentum with value (P/VP). Stocks with positive price trends that are still reasonably valued. The two factors are ranked independently and combined 50/50. This is orthogonal to all other strategies since it's the only one using price momentum.

**Step 1: Add pipeline class to `stocks/pipelines.py`**

```python
class MomentumValuePipeline(ScreeningPipeline):
    """Momentum + Value: combines 12-month price trend with P/VP valuation.

    Ranks by 12-month price momentum (higher is better) and P/VP
    (lower is better), combined 50/50. Captures trending stocks
    that aren't overpriced. Only strategy that uses price momentum.
    """

    output_path = "momentum_value.json"

    def filter(self, items):
        """Base filter plus require 12-month momentum data and positive P/VP."""
        base = super().filter(items)
        return [
            item for item in base
            if self._get_nested(item, "Oscilações", "12 meses", None) is not None
            and (self._get_nested(item, "Indicadores fundamentalistas", "P/VP", 0) or 0) > 0
        ]

    def rank(self, items):
        for item in items:
            item["_momentum"] = self._get_nested(item, "Oscilações", "12 meses", float("-inf"))
            item["_pvp"] = self._get_nested(item, "Indicadores fundamentalistas", "P/VP", float("inf"))

        # Rank momentum: higher is better
        items.sort(key=lambda x: x["_momentum"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Momentum"] = rank

        # Rank P/VP: lower is better
        items.sort(key=lambda x: x["_pvp"])
        for rank, item in enumerate(items, 1):
            item["Rank P/VP"] = rank

        for item in items:
            item["Rank Momentum+Value"] = item["Rank Momentum"] + item["Rank P/VP"]
            del item["_momentum"]
            del item["_pvp"]

        items.sort(key=lambda x: x["Rank Momentum+Value"])
        return items
```

**Step 2: Register in spider**

Add to `ITEM_PIPELINES`:
```python
"stocks.pipelines.MomentumValuePipeline": 700,
```

**Step 3: Add `momentum_value.json` to `.gitignore`**

**Step 4: Run checks**

```bash
just check
```

**Step 5: Commit**

```bash
git add stocks/pipelines.py stocks/spiders/fundamentus.py .gitignore
git commit -m "feat: add Momentum+Value pipeline (12m price trend + P/VP)"
```

---

### Task 6: ContrarianPipeline

**Files:**
- Modify: `stocks/pipelines.py`
- Modify: `stocks/spiders/fundamentus.py:28-41`
- Modify: `.gitignore`

**Description:** 52-Week Low Contrarian. Finds stocks trading near their 52-week low (within 20%) that still have strong fundamentals (ROIC > 10%, low debt). Mean-reversion play with a quality floor. Ranked by proximity to 52-week low.

**Step 1: Add pipeline class to `stocks/pipelines.py`**

```python
class ContrarianPipeline(ScreeningPipeline):
    """52-Week Low Contrarian: beaten-down stocks with strong fundamentals.

    Finds stocks within 20% of their 52-week low that maintain
    ROIC > 10% and Debt/Equity < 1.5. Mean-reversion play with
    a quality floor. Ranked by proximity to 52-week low.
    """

    output_path = "contrarian.json"
    MAX_ABOVE_52W_LOW = 0.20  # Within 20% of 52-week low
    MIN_ROIC = 0.10
    MAX_DEBT_RATIO = 1.5

    def filter(self, items):
        base = super().filter(items)
        result = []
        for item in base:
            cotacao = item.get("Cotação", 0) or 0
            min_52 = item.get("Min 52 sem", 0) or 0
            roic = self._get_nested(item, "Oscilações", "ROIC", 0) or 0
            debt = self._get_nested(item, "Oscilações", "Div Br/ Patrim", float("inf")) or 0

            if min_52 > 0 and cotacao > 0 and roic >= self.MIN_ROIC and debt <= self.MAX_DEBT_RATIO:
                above_low = (cotacao - min_52) / min_52
                if above_low <= self.MAX_ABOVE_52W_LOW:
                    result.append(item)
        return result

    def rank(self, items):
        for item in items:
            cotacao = item.get("Cotação", 0)
            min_52 = item.get("Min 52 sem", 1)
            item["Above 52w Low"] = round((cotacao - min_52) / min_52, 4) if min_52 > 0 else float("inf")

        items.sort(key=lambda x: x["Above 52w Low"])
        for rank, item in enumerate(items, 1):
            item["Rank Contrarian"] = rank

        return items
```

**Step 2: Register in spider**

Add to `ITEM_PIPELINES`:
```python
"stocks.pipelines.ContrarianPipeline": 700,
```

**Step 3: Add `contrarian.json` to `.gitignore`**

**Step 4: Run checks**

```bash
just check
```

**Step 5: Commit**

```bash
git add stocks/pipelines.py stocks/spiders/fundamentus.py .gitignore
git commit -m "feat: add Contrarian pipeline (52-week low + quality fundamentals)"
```

---

### Task 7: CashRichPipeline

**Files:**
- Modify: `stocks/pipelines.py`
- Modify: `stocks/spiders/fundamentus.py:28-41`
- Modify: `.gitignore`

**Description:** Finds companies with large cash reserves relative to market cap (Disponibilidades / Valor de mercado). High cash-to-market-cap ratio signals hidden value or takeover potential. Ranked by cash ratio.

**Step 1: Add pipeline class to `stocks/pipelines.py`**

```python
class CashRichPipeline(ScreeningPipeline):
    """Cash-Rich Companies: high cash reserves relative to market cap.

    Ranks by Disponibilidades / Valor de mercado. Companies sitting on
    large cash piles relative to their market cap may signal hidden
    value or takeover potential.
    """

    output_path = "cashrich.json"

    def filter(self, items):
        base = super().filter(items)
        return [
            item for item in base
            if (self._get_nested(item, "Dados Balanço Patrimonial", "Disponibilidades", 0) or 0) > 0
            and (item.get("Valor de mercado", 0) or 0) > 0
        ]

    def rank(self, items):
        for item in items:
            cash = self._get_nested(item, "Dados Balanço Patrimonial", "Disponibilidades", 0)
            market_cap = item.get("Valor de mercado", 1)
            item["Cash / Market Cap"] = round(cash / market_cap, 4) if market_cap > 0 else 0

        items.sort(key=lambda x: x["Cash / Market Cap"], reverse=True)
        for rank, item in enumerate(items, 1):
            item["Rank Cash-Rich"] = rank

        return items
```

**Step 2: Register in spider**

Add to `ITEM_PIPELINES`:
```python
"stocks.pipelines.CashRichPipeline": 700,
```

**Step 3: Add `cashrich.json` to `.gitignore`**

**Step 4: Run checks**

```bash
just check
```

**Step 5: Commit**

```bash
git add stocks/pipelines.py stocks/spiders/fundamentus.py .gitignore
git commit -m "feat: add Cash-Rich pipeline (cash/market cap screening)"
```

---

### Task 8: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:37-45`

**Step 1: Update screening pipelines list**

Add the 7 new pipelines to the screening pipelines section:

```markdown
   - `AcquirersMultiplePipeline`: EV/EBITDA only (Tobias Carlisle) → `acquirers.json`
   - `DeepValuePipeline`: P/L + P/VP + PSR + EV/EBITDA composite rank → `deepvalue.json`
   - `NetNetPipeline`: stocks below NCAV liquidation value → `netnet.json`
   - `GARPPipeline`: PEG ratio (P/L / 5y growth) → `garp.json`
   - `MomentumValuePipeline`: 12-month momentum + P/VP → `momentum_value.json`
   - `ContrarianPipeline`: near 52-week low + strong fundamentals → `contrarian.json`
   - `CashRichPipeline`: cash reserves / market cap → `cashrich.json`
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with new screening pipelines"
```
