# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Brazilian stock market analysis system that scrapes fundamental data from Fundamentus, applies the Magic Formula investment strategy, and generates portfolio recommendations. Uses Scrapy for web scraping and includes a simple web frontend.

## Build & Run Commands

```bash
# Install dependencies
just sync

# Run the Fundamentus spider (outputs fundamentus.json + all strategy JSONs)
just crawl

# Cross-validate Fundamentus data against StatusInvest (all tickers, slow)
just crossval

# Cross-validate specific tickers only
just crossval-tickers VULC3,WEGE3,PETR4

# Lint and type check
just check

# Lint only / type check only
just lint
just typecheck

# Auto-fix lint issues
just lint-fix

# Format code
just fmt
```

## Architecture

**Data pipeline flow (all triggered by `just crawl`):**
1. **Spider** (`stocks/spiders/fundamentus.py`) scrapes Fundamentus stock listings and detail pages
2. **Transform pipelines** (`stocks/pipelines.py`): Clean → Normalize (Brazilian number formats) → DateValues → NaN handling
3. **Enrichment pipelines**: DataSources (adds URLs to Fundamentus/StatusInvest/Investidor10/Yahoo/Google/TradingView) → AnomalyDetection (flags outliers, inconsistencies, suspicious values → `data/intelligence/anomalies.json`)
3. **Screening pipelines** (`stocks/pipelines.py`), all sharing base filtering (liquidity ≥ 150k, EBIT margin > 0, excluded financial sectors):
   - `MagicFormulaPipeline`: EV/EBIT + ROIC combined rank → `magicformula.json`
   - `CDVPipeline`: EV/EBIT only (Clube do Valor) → `cdv.json`
   - `IntersectionPipeline`: stocks in both Magic Formula and CDV top-30 → `intersection.json`
   - `GrahamNumberPipeline`: margin of safety vs Graham Number (√(22.5×LPA×VPA)) → `graham.json`
   - `BazinPipeline`: Div. Yield ≥ 6%, low debt, ranked by yield → `bazin.json`
   - `QualityPipeline`: ROIC + net margin combined rank → `quality.json`
   - `PiotroskiPipeline`: simplified F-Score (≥ 6 of 9 signals) → `piotroski.json`
   - `MultiFactorPipeline`: weighted blend of value/quality/growth/income → `multifactor.json`
   - `AcquirersMultiplePipeline`: EV/EBITDA only (Tobias Carlisle) → `acquirers.json`
   - `DeepValuePipeline`: P/L + P/VP + PSR + EV/EBITDA composite rank → `deepvalue.json`
   - `NetNetPipeline`: stocks below NCAV liquidation value → `netnet.json`
   - `GARPPipeline`: PEG ratio (P/L / 5y growth) → `garp.json`
   - `MomentumValuePipeline`: 12-month momentum + P/VP → `momentum_value.json`
   - `ContrarianPipeline`: near 52-week low + strong fundamentals → `contrarian.json`
   - `CashRichPipeline`: cash reserves / market cap → `cashrich.json`
   - `DuPontQualityPipeline`: ROE decomposition penalizing leverage → `dupont.json`
   - `SmallCapValuePipeline`: bottom quartile market cap + EV/EBIT → `smallcap_value.json`
   - `LargeCapDividendPipeline`: top quartile market cap + high yield + low debt → `largecap_dividend.json`
   - `SectorRelativeValuePipeline`: cheapest quartile within each sector → `sector_relative.json`
   - `EarningsAccelerationPipeline`: annualized 3m vs 12m earnings trend → `earnings_accel.json`
   - `AssetLightQualityPipeline`: ROIC + asset turnover → `assetlight.json`
   - `AltmanZScorePipeline`: simplified bankruptcy risk filter (Z ≥ 1.8) → `altman.json`
   - `BookValueDiscountPipeline`: P/VP < 1, ranked by discount → `bookvalue.json`
   - `WorkingCapitalValuePipeline`: P/Cap. Giro + P/Ativ Circ Liq ranking → `working_capital.json`
   - `MarginCompressionPipeline`: gross vs EBIT margin gap → `margin_compression.json`
   - `FortressBalanceSheetPipeline`: high liquidity + low debt → `fortress.json`
   - `RedFlagPipeline`: inverse screen counting warning signals → `redflags.json`
   - `EarningsYieldSpreadPipeline`: EBIT/EV yield minus Selic rate → `earnings_yield_spread.json`
   - `BuffettCompositePipeline`: ROE > 15%, low debt, margins, reasonable P/L → `buffett.json`
   - `VolatilityAdjustedValuePipeline`: EV/EBIT penalized by 52w price range → `volatility_adjusted.json`
   - `ConsensusScreenPipeline`: meta-strategy, stocks in 5+ other strategies → `consensus.json`
4. **FEEDS** export writes raw data to `fundamentus.json`
5. **Frontend** (`frontend/index.html`) displays the portfolio using Bulma CSS

**Key data transformations** in pipelines:
- Brazilian number format `1.234,56` → float `1234.56`
- Percentage strings `15,5%` → decimal `0.155`
- Dates `01/01/2024` → ISO `2024-01-01`

**Cross-validation spider** (`stocks/spiders/statusinvest.py`): Scrapes StatusInvest for the same tickers and compares 10 key metrics (P/L, P/VP, ROE, margins, etc.) with 15% tolerance. Outputs discrepancy report to `data/intelligence/cross_validation.json`. Run via `just crossval` or `just crossval-tickers TICKER1,TICKER2`.

**WIP:** `stocks/spiders/b3.py` — B3 FII spider, incomplete. The B3 page loads data via JavaScript/iframe and needs dynamic content handling.

## Key Technologies

- **Scrapy** + Spidermon for web scraping
- **Pandas/Polars** for data processing
- **uv** for package management (`pyproject.toml` + `uv.lock`)
- **ruff** for linting and formatting
- **ty** for type checking
- **just** as task runner
