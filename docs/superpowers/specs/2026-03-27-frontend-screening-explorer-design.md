# Frontend Screening Explorer Design

Date: 2026-03-27
Status: Approved for planning

## 1. Objective

Build a static frontend to explore stock-screening results across multiple strategies, compare strategies, compute intersections dynamically, and surface risk warnings per stock with transparent rules.

The frontend must prioritize strategy exploration and editorial context while keeping high information density. It must consume strategy metadata directly from each strategy output and also use a generated bundle for runtime loading.

## 2. Scope

### In Scope (v1)

- Strategy-first interface in `pt-BR`
- Auto-discovery of strategy outputs for bundling
- Strategy JSON outputs enriched with metadata and context
- Post-crawl bundle generation for frontend consumption
- Strategy comparison in a right-side drawer with `AND`/`OR`
- Intersection results computed client-side in real time
- Risk badge on stock cards (`BAIXO`/`MÉDIO`/`ALTO`)
- Detailed risk breakdown in stock detail drawer
- Swiss International visual system adapted to a terminal/editorial blend

### Out of Scope (v1)

- Backend API
- User auth or server persistence
- Real-time market feeds
- Portfolio execution flows (buy/sell)

## 3. Data Architecture

### 3.1 Strategy Output Contract (source of truth)

Each strategy file must include top-level metadata and `stocks`.

Required top-level fields:

- `strategy_id`
- `name`
- `description`
- `methodology_summary`
- `use_cases` (array of strings)
- `caveats` (array of strings)
- `generated_at`
- `universe_size`
- `filtered_size`
- `result_size`
- `stocks` (array)

Each stock entry should preserve strategy-specific ranking fields and include enough shared fields for comparison/risk:

- `Papel`, `Empresa`, `Setor`, `Subsetor`
- `Cotação`, `Liq.2meses`, `Min 52 sem`, `Max 52 sem`
- Relevant nested metric sections used by risk and UI (`Oscilações`, `Indicadores fundamentalistas`, `Dados Balanço Patrimonial`), when available

### 3.2 Bundle Generation

After crawl completion, generate:

- `frontend/data/strategies.bundle.json`

Bundle shape:

- `generated_at`
- `strategies` (array of strategy payloads)
- Optional optimization indexes (e.g., `stock_index: ticker -> strategy_ids`) for fast client intersections

Frontend runtime reads only the bundle.

## 4. UX and Information Architecture

### 4.1 Primary Home View

- Strategy-first home
- Compact manifesto strip on top
- Main area starts immediately with strategy list in editorial cards

Card content:

- Strategy name
- Short description
- `Quando usar`
- `Caveats`
- Result count
- Actions: `Ver ativos`, `Comparar`

### 4.2 Comparison and Intersections

- Comparison flow lives in a right-side drawer (no page navigation)
- Multi-select strategies
- Operator switch `AND` / `OR`
- Real-time ticker result set
- Coverage indicators (absolute count + percentage over bundle universe)
- Optional local preset saving in browser storage

### 4.3 Risk Presentation

- Stock cards show a minimal risk badge only
- Full risk analysis appears in stock detail drawer
- Risk model is deterministic and transparent (rule-based, no ML)

Output model:

- `risk_level`: `BAIXO` | `MÉDIO` | `ALTO`
- `risk_score`: internal numeric score
- `risk_flags`: triggered rules with explanations

Initial rules:

- `liquidez_baixa`
- `endividamento_alto`
- `margem_ebit_fraca`
- `volatilidade_12m_alta`
- `sinais_incompletos`

## 5. Visual Design System (Swiss + Editorial Terminal)

### 5.1 Design Direction

- Swiss International Typographic Style with objective, grid-led communication
- Mixture of dense information blocks and editorial readability
- Strict rectangular geometry, visible structure, asymmetry, and active negative space

### 5.2 Core Tokens

- Background: `#FFFFFF`
- Foreground: `#000000`
- Muted: `#F2F2F2`
- Accent: `#FF3000`
- Border: `#000000`
- Radius: `0`
- Shadows: none

Typography:

- Family: Inter (or existing closest grotesque sans fallback)
- Uppercase labels/headings where appropriate
- Strong contrast in scale and weight
- Left-aligned text, ragged-right blocks

### 5.3 Surfaces and Interaction

- Editorial strategy cards (default list format)
- Borders define structure
- Subtle textures on neutral surfaces (grid/dots/noise), never on black/red fills
- Mechanical transitions (fast, geometric, no spring feel)
- High-contrast focus states and minimum mobile touch targets

## 6. Error Handling and Resilience

- Missing bundle: show actionable state instructing user to run crawl/bundle generation
- Invalid schema: report missing top-level fields and isolate broken strategy payload
- Empty strategy result: show valid empty card state
- Missing stock fields: risk engine adds `sinais_incompletos` flag, UI remains functional

## 7. Testing and Verification Strategy

### 7.1 Data-side tests (Python)

- Contract test for every strategy JSON output
- Bundler tests validating output schema and indexing integrity

### 7.2 Frontend tests

- Unit tests for `AND`/`OR` intersection logic
- Unit tests for risk scoring and rule-flag emission
- Rendering tests for empty/error/degraded states

### 7.3 Smoke flow

1. Run crawl
2. Confirm strategy JSON outputs with metadata
3. Confirm bundle generation
4. Open frontend and verify strategy list rendering
5. Verify compare drawer intersections
6. Verify stock risk detail drawer explanations

## 8. Implementation Notes for Next Phase

- Keep source-of-truth metadata in each strategy output as requested
- Generate frontend bundle as an explicit final step after crawl
- Keep frontend static-only in v1; structure data access with clear adapter boundaries for future API migration

## 9. Acceptance Criteria

- All strategy outputs include required metadata and `stocks`
- Bundle file is generated and consumed by frontend
- Home is strategy-first with editorial cards in `pt-BR`
- Compare drawer supports multi-strategy `AND`/`OR` intersections
- Each stock shows risk badge; detail drawer shows rule-based breakdown
- Swiss-style visual system is consistently applied across desktop/mobile with accessibility intact
