# Frontend UX Improvements Design

## Goal

Redesign the frontend information hierarchy so regular Brazilian investors can quickly answer two questions: "Which strategy fits my profile?" and "What do strategies say about ticker X?"

## Audience

Average Brazilian retail investors exploring quantitative strategies. They don't know what EV/EBIT or ROIC means without context. They want clear, progressive disclosure: simple first, detail on demand.

## Primary User Flows

1. **Compare strategies by profile** — Browse strategies grouped by investment philosophy, compare stats visually, then deep-dive into a dedicated comparison view.
2. **Validate a specific ticker** — Search for a ticker and see a unified profile: key metrics, risk level, every strategy that includes it with rank position, anomalies, and external source links.

---

## Changes

### 1. Compact Header

Replace the current hero section (big title, subtitle, padded layout) with a slim bar containing: title, timestamp, universe count, and controls (Top N select, Sector filter). Reclaim vertical space so actionable content is above the fold.

### 2. Ticker Search Bar

Sticky bar below the header. Autocomplete against all tickers in the bundle's `stock_index`. Dropdown shows ticker + company name.

**Ticker Profile** — opens inline (replaces main content, with a back button):
- Logo, ticker, company name, sector
- Source links (F, SI, I10, Y, G, TV)
- Metrics grid: P/L, P/VP, DY, ROIC, Marg. EBIT, Risco
- Table of every strategy that includes this ticker: strategy name, rank position, category
- Anomaly summary with flags or "clean" confirmation

All tickers throughout the UI (consensus picks, strategy tables, intersection results) are clickable and open this same profile.

### 3. Persona Category Tabs

Horizontal tab bar replacing the flat strategy index nav. Tabs: Valor, Qualidade, Renda, Crescimento, Risco, Compostas, Todos.

Each tab displays a user-story persona and filters the strategy list below.

| Category | User Story | Strategies |
|-----------|-----------|------------|
| Valor | "Quero encontrar ações que o mercado está precificando abaixo do que valem" | Magic Formula, Graham, Deep Value, Acquirers, Net-Net, Book Value, Working Capital, Sector Relative |
| Qualidade | "Quero empresas lucrativas, bem geridas e com balanço sólido" | Quality, DuPont, Buffett, Asset Light, Fortress, Altman Z-Score |
| Renda | "Quero ações que pagam bons dividendos de forma consistente" | Bazin, Large Cap Dividend, Earnings Yield Spread, Cash Rich |
| Crescimento | "Quero empresas que estão crescendo rápido sem pagar caro por isso" | GARP, Earnings Acceleration, Momentum Value, Small Cap Value |
| Risco | "Quero entender onde estão os riscos e oportunidades que outros ignoram" | Contrarian, Piotroski, Red Flags, Volatility Adjusted, Margin Compression |
| Compostas | "Quero ver o que acontece quando cruzo múltiplas estratégias" | Multi-Factor, CDV, Intersection, Consensus |

### 4. Enhanced Strategy Cards

Add to each card (below description, above ticker pills):

- **Summary stat box**: filtered → ranked count, category-relevant avg metrics, risk distribution mini-bar
- Category-specific avg metrics:
  - Valor: avg P/L, avg P/VP
  - Renda: avg DY, avg Div/Patrim
  - Qualidade: avg ROIC, avg Marg. Líquida
  - Crescimento/Risco/Compostas: avg P/L, avg DY
- **Risk distribution mini-bar**: horizontal stacked bar showing % BAIXO / MEDIO / ALTO
- Rename "Interseção" button to "Comparar"

### 5. Comparison View

Replaces the current right-side drawer (520px). Full-width inline section that pushes content down when opened. Max 2-4 strategies.

Layout:
- Side-by-side columns, one per selected strategy
- Each column shows: strategy name, category, stock count, avg metrics (DY, P/L, ROIC), risk distribution bar, top 5 tickers
- Overlap markers (dot) on tickers present in multiple selected strategies
- Intersection/union result at bottom with AND/OR toggle and copy button

### 6. Reordered Page Sections

New order:
1. Compact header (slim bar)
2. Ticker search bar (sticky)
3. Persona category tabs + user story
4. Strategy cards (filtered by active tab)
5. Consensus picks (moved down — supporting evidence, not entry point)
6. Intelligence section (data quality reference, unchanged)

### 7. What Stays the Same

- Strategy detail panels (split layout, charts, quant analysis, tables)
- Risk evaluation logic (`risk.mjs`)
- All data pipelines and bundle format
- Intelligence rendering (anomaly tables, severity toggle)
- Source link badges and anomaly badge rendering
- Intersection/union logic (`intersections.mjs`)

### 8. What Gets Removed

- Hero section large padding, subtitle, and `swiss-grid-pattern` background
- Right-side drawer (`aside#compare-drawer`, 520px fixed)
- Flat strategy index nav (replaced by category tabs)
- Usage panel explaining intersection (comparison view is self-explanatory)
