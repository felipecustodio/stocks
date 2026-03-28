# Frontend UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the frontend so regular Brazilian investors can compare strategies by profile and look up any ticker across all strategies.

**Architecture:** Pure vanilla JS (ES6 modules), no framework. All data comes from `strategies.bundle.json` loaded at boot. State lives in a single `state` object in `main.mjs`. Rendering is imperative DOM manipulation in `render.mjs`. CSS is a single `styles.css` file with CSS custom properties.

**Tech Stack:** Vanilla JS (ES6 modules), CSS custom properties, Chart.js (charts), MathJax (LaTeX), Lucide (icons)

---

### Task 1: Add category mapping data module

**Files:**
- Create: `frontend/js/categories.mjs`
- Test: `frontend/tests/categories.test.mjs`

**Step 1: Write the test**

```javascript
// frontend/tests/categories.test.mjs
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { CATEGORIES, categoryForStrategy } from '../js/categories.mjs';

describe('categories', () => {
  it('maps magicformula to valor', () => {
    assert.equal(categoryForStrategy('magicformula'), 'valor');
  });

  it('maps bazin to renda', () => {
    assert.equal(categoryForStrategy('bazin'), 'renda');
  });

  it('maps unknown strategy to null', () => {
    assert.equal(categoryForStrategy('nonexistent'), null);
  });

  it('every category has a label, story, and strategies array', () => {
    for (const cat of CATEGORIES) {
      assert.ok(cat.id, 'missing id');
      assert.ok(cat.label, 'missing label');
      assert.ok(cat.story, 'missing story');
      assert.ok(Array.isArray(cat.strategies) && cat.strategies.length > 0, 'missing strategies');
    }
  });

  it('has a todos entry that contains no strategies', () => {
    const todos = CATEGORIES.find((c) => c.id === 'todos');
    assert.ok(todos);
    assert.equal(todos.strategies.length, 0);
  });

  it('categoryMetrics returns 2 metrics for each category', () => {
    // Imported separately
    const { categoryMetrics } = await import('../js/categories.mjs');
    for (const cat of CATEGORIES) {
      if (cat.id === 'todos') continue;
      const metrics = categoryMetrics(cat.id);
      assert.equal(metrics.length, 2, `${cat.id} should have 2 metrics`);
      assert.ok(metrics[0].label, `${cat.id} metric 0 missing label`);
      assert.ok(metrics[0].path, `${cat.id} metric 0 missing path`);
    }
  });
});
```

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/categories.test.mjs`
Expected: FAIL — module not found

**Step 3: Write the implementation**

```javascript
// frontend/js/categories.mjs

export const CATEGORIES = [
  {
    id: 'todos',
    label: 'Todos',
    story: '',
    icon: 'layout-grid',
    strategies: [],
  },
  {
    id: 'valor',
    label: 'Valor',
    story: 'Quero encontrar ações que o mercado está precificando abaixo do que valem',
    icon: 'search',
    strategies: [
      'magicformula', 'graham', 'deepvalue', 'acquirers',
      'netnet', 'bookvalue', 'working_capital', 'sector_relative',
    ],
  },
  {
    id: 'qualidade',
    label: 'Qualidade',
    story: 'Quero empresas lucrativas, bem geridas e com balanço sólido',
    icon: 'award',
    strategies: ['quality', 'dupont', 'buffett', 'assetlight', 'fortress', 'altman'],
  },
  {
    id: 'renda',
    label: 'Renda',
    story: 'Quero ações que pagam bons dividendos de forma consistente',
    icon: 'wallet',
    strategies: ['bazin', 'largecap_dividend', 'earnings_yield_spread', 'cashrich'],
  },
  {
    id: 'crescimento',
    label: 'Crescimento',
    story: 'Quero empresas que estão crescendo rápido sem pagar caro por isso',
    icon: 'trending-up',
    strategies: ['garp', 'earnings_accel', 'momentum_value', 'smallcap_value'],
  },
  {
    id: 'risco',
    label: 'Risco',
    story: 'Quero entender onde estão os riscos e oportunidades que outros ignoram',
    icon: 'shield-alert',
    strategies: ['contrarian', 'piotroski', 'redflags', 'volatility_adjusted', 'margin_compression'],
  },
  {
    id: 'compostas',
    label: 'Compostas',
    story: 'Quero ver o que acontece quando cruzo múltiplas estratégias',
    icon: 'layers',
    strategies: ['multifactor', 'cdv', 'intersection', 'consensus'],
  },
];

const _strategyToCategory = new Map();
for (const cat of CATEGORIES) {
  for (const sid of cat.strategies) {
    _strategyToCategory.set(sid, cat.id);
  }
}

export function categoryForStrategy(strategyId) {
  return _strategyToCategory.get(strategyId) ?? null;
}

const _categoryMetrics = {
  valor: [
    { label: 'P/L médio', path: ['Indicadores fundamentalistas', 'P/L'] },
    { label: 'P/VP médio', path: ['Indicadores fundamentalistas', 'P/VP'] },
  ],
  qualidade: [
    { label: 'ROIC médio', path: ['Oscilações', 'ROIC'] },
    { label: 'Marg. Líq. média', path: ['Oscilações', 'Marg. Líquida'] },
  ],
  renda: [
    { label: 'DY médio', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
    { label: 'Dív/PL médio', path: ['Oscilações', 'Div Br/ Patrim'] },
  ],
  crescimento: [
    { label: 'P/L médio', path: ['Indicadores fundamentalistas', 'P/L'] },
    { label: 'DY médio', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
  ],
  risco: [
    { label: 'P/L médio', path: ['Indicadores fundamentalistas', 'P/L'] },
    { label: 'DY médio', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
  ],
  compostas: [
    { label: 'P/L médio', path: ['Indicadores fundamentalistas', 'P/L'] },
    { label: 'DY médio', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
  ],
};

export function categoryMetrics(categoryId) {
  return _categoryMetrics[categoryId] ?? _categoryMetrics.compostas;
}
```

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/categories.test.mjs`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/js/categories.mjs frontend/tests/categories.test.mjs
git commit -m "feat(frontend): add category mapping data module"
```

---

### Task 2: Add ticker index builder to data.mjs

This builds a lookup from ticker → full stock data + all strategy appearances with rank, needed for the ticker profile view.

**Files:**
- Modify: `frontend/js/data.mjs`
- Test: `frontend/tests/data.test.mjs`

**Step 1: Write the test**

```javascript
// frontend/tests/data.test.mjs
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { buildTickerIndex } from '../js/data.mjs';

describe('buildTickerIndex', () => {
  const strategies = [
    {
      strategy_id: 'magic',
      name: 'Magic Formula',
      stocks: [
        { Papel: 'WEGE3', Empresa: 'WEG S.A.', Setor: 'Máquinas', Fontes: { F: 'http://f' } },
        { Papel: 'VALE3', Empresa: 'Vale S.A.', Setor: 'Mineração' },
      ],
    },
    {
      strategy_id: 'quality',
      name: 'Quality',
      stocks: [
        { Papel: 'WEGE3', Empresa: 'WEG S.A.', Setor: 'Máquinas' },
      ],
    },
  ];

  it('builds index with ticker as key', () => {
    const index = buildTickerIndex(strategies);
    assert.ok(index.has('WEGE3'));
    assert.ok(index.has('VALE3'));
    assert.equal(index.size, 2);
  });

  it('tracks all strategy appearances with rank', () => {
    const index = buildTickerIndex(strategies);
    const wege = index.get('WEGE3');
    assert.equal(wege.appearances.length, 2);
    assert.equal(wege.appearances[0].strategy_id, 'magic');
    assert.equal(wege.appearances[0].rank, 1);
    assert.equal(wege.appearances[1].strategy_id, 'quality');
    assert.equal(wege.appearances[1].rank, 1);
  });

  it('keeps company and sector from first appearance', () => {
    const index = buildTickerIndex(strategies);
    const wege = index.get('WEGE3');
    assert.equal(wege.company, 'WEG S.A.');
    assert.equal(wege.sector, 'Máquinas');
  });

  it('merges fontes from all appearances', () => {
    const index = buildTickerIndex(strategies);
    const wege = index.get('WEGE3');
    assert.deepEqual(wege.fontes, { F: 'http://f' });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/data.test.mjs`
Expected: FAIL — buildTickerIndex not exported

**Step 3: Add `buildTickerIndex` to `data.mjs`**

Append to `frontend/js/data.mjs`:

```javascript
export function buildTickerIndex(strategies) {
  const index = new Map();
  for (const strategy of strategies) {
    for (let i = 0; i < strategy.stocks.length; i++) {
      const stock = strategy.stocks[i];
      if (!stock?.Papel) continue;
      const ticker = stock.Papel;

      if (!index.has(ticker)) {
        index.set(ticker, {
          ticker,
          company: stock.Empresa ?? '',
          sector: stock.Setor ?? '',
          sample: stock,
          fontes: { ...(stock.Fontes ?? {}) },
          appearances: [],
        });
      }

      const entry = index.get(ticker);
      // Merge fontes from each appearance
      if (stock.Fontes) {
        Object.assign(entry.fontes, stock.Fontes);
      }

      entry.appearances.push({
        strategy_id: strategy.strategy_id,
        strategy_name: strategy.name,
        rank: i + 1,
        total: strategy.stocks.length,
      });
    }
  }
  return index;
}
```

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/data.test.mjs`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/js/data.mjs frontend/tests/data.test.mjs
git commit -m "feat(frontend): add buildTickerIndex for unified ticker lookup"
```

---

### Task 3: Compact header + reordered HTML structure

Replace the hero section with a slim header bar. Reorder HTML sections: header → search → categories → strategies → consensus → intelligence. Remove the drawer aside, usage panel, and flat strategy index nav.

**Files:**
- Modify: `frontend/index.html`

**Step 1: Rewrite `index.html`**

Replace the full `<body>` content. The new structure:

```html
<body>
  <main class="page">
    <!-- Compact header -->
    <header class="site-header">
      <h1 class="site-title">Atlas Quantitativo</h1>
      <div class="header-controls">
        <span class="meta-pill">
          <i data-lucide="database"></i>
          <span id="status">Inicializando...</span>
        </span>
        <span class="meta-pill">
          <i data-lucide="calendar"></i>
          <strong id="generated-at">-</strong>
        </span>
        <span class="meta-pill">
          <i data-lucide="chart-candlestick"></i>
          <strong id="universe-count">-</strong> ações
        </span>
        <span class="meta-pill meta-control">
          <label for="display-limit">Top N:</label>
          <select id="display-limit">
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="30" selected>30</option>
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="ALL">ALL</option>
          </select>
        </span>
        <span class="meta-pill meta-control">
          <label for="sector-filter">Setor:</label>
          <select id="sector-filter">
            <option value="ALL" selected>Todos</option>
          </select>
        </span>
      </div>
    </header>

    <!-- Ticker search -->
    <section class="search-section">
      <div class="search-box">
        <i data-lucide="search"></i>
        <input id="ticker-search" type="text" placeholder="Buscar ativo: WEGE3, VALE3..." autocomplete="off" />
        <div id="search-results" class="search-dropdown"></div>
      </div>
    </section>

    <!-- Ticker profile (hidden by default) -->
    <section id="ticker-profile" class="ticker-profile" style="display:none"></section>

    <!-- Category tabs -->
    <section class="categories-section">
      <nav id="category-tabs" class="category-tabs" aria-label="Categorias de estratégia"></nav>
      <p id="category-story" class="category-story"></p>
    </section>

    <!-- Strategy cards -->
    <section class="strategies-section">
      <div id="strategies" class="strategy-list"></div>
    </section>

    <!-- Comparison view (hidden by default, full-width inline) -->
    <section id="comparison-view" class="comparison-view" style="display:none"></section>

    <!-- Consensus picks -->
    <section class="consensus-section">
      <p class="section-label">TOP PICKS DE CONSENSO</p>
      <div class="consensus-head">
        <h2><i data-lucide="sparkles"></i> Ações Mais Recorrentes</h2>
        <p class="muted">
          Papéis que aparecem com maior frequência entre as estratégias ativas.
        </p>
      </div>
      <div id="consensus-picks" class="consensus-picks"></div>
    </section>

    <!-- Intelligence -->
    <section id="intelligence-section" class="intelligence-section swiss-grid-pattern" style="display:none">
      <p class="section-label">INTELIGÊNCIA DE DADOS</p>
      <div class="intelligence-head">
        <h2><i data-lucide="scan-search"></i> Qualidade dos Dados</h2>
        <p class="muted">
          Anomalias detectadas automaticamente: métricas fora da faixa, inconsistências entre campos e outliers estatísticos.
        </p>
      </div>
      <div class="intelligence-summary">
        <div class="intel-stat-grid" id="intel-stats"></div>
      </div>
      <div class="intel-table-wrap" id="intel-anomalies-wrap" style="display:none">
        <h3><i data-lucide="alert-triangle"></i> Alertas de Alta Severidade</h3>
        <div class="table-scroll">
          <table class="stocks-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Setor</th>
                <th>Severidade</th>
                <th>Flags</th>
                <th>Detalhes</th>
                <th>Fontes</th>
              </tr>
            </thead>
            <tbody id="intel-anomalies-body"></tbody>
          </table>
        </div>
        <button class="btn" id="intel-toggle-all" style="margin-top:12px">
          <i data-lucide="chevron-down"></i> <span>Mostrar médias e baixas</span>
        </button>
        <div class="table-scroll" id="intel-all-wrap" style="display:none">
          <table class="stocks-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Setor</th>
                <th>Severidade</th>
                <th>Flags</th>
                <th>Detalhes</th>
                <th>Fontes</th>
              </tr>
            </thead>
            <tbody id="intel-all-body"></tbody>
          </table>
        </div>
      </div>
    </section>
  </main>

  <script type="module" src="./main.mjs"></script>
  <script src="https://unpkg.com/lucide@0.539.0/dist/umd/lucide.min.js"></script>
</body>
```

Key changes from current HTML:
- Hero replaced with `.site-header` (slim, single line)
- No subtitle, no hero-subtitle, no swiss-grid-pattern on hero
- `#ticker-search` input + `#search-results` dropdown added
- `#ticker-profile` empty section added (rendered by JS)
- `#category-tabs` nav + `#category-story` paragraph added
- Strategy nav (`.strategy-nav`) removed
- Usage panel (`.usage-panel`) removed
- `<aside id="compare-drawer">` removed entirely
- `#comparison-view` section added (inline, full-width)
- Consensus moved after strategies
- Section label numbers removed (no more 01., 02., etc.)
- MathJax + Chart.js scripts stay in `<head>`

**Step 2: Verify the page loads without JS errors**

Run: `python3 -m http.server -d frontend 8000 &` then open browser.
Expected: Page loads, shows "Inicializando..." then strategy data. Some features broken until JS is updated (next tasks).

**Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat(frontend): compact header, reorder sections, remove drawer"
```

---

### Task 4: Update CSS for new layout

Remove old hero/drawer/usage-panel/strategy-nav styles. Add new styles for compact header, search bar, category tabs, ticker profile, and comparison view.

**Files:**
- Modify: `frontend/styles.css`

**Step 1: Remove old styles**

Delete these CSS blocks:
- `.hero` block and all hero-related selectors (`.hero h1`, `.hero-subtitle`)
- `.strategy-nav`, `.strategy-nav-title`, `.strategy-index`, `.strategy-index-item` (all)
- `.usage-panel` and all children (`.usage-steps`, etc.)
- `.drawer` and all children (`.drawer-head`, `.drawer-body`, `.drawer-help`, `.mode-badge`, `.drawer-subtitle`)
- `.consensus-section` number label (`02.` etc.)

**Step 2: Add new styles**

```css
/* ── Compact header ── */

.site-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  border: 3px solid var(--border);
  padding: 0.5rem 0.75rem;
  background: var(--bg);
}

.site-title {
  margin: 0;
  font-size: 1.15rem;
  text-transform: uppercase;
  letter-spacing: -0.02em;
  white-space: nowrap;
}

.header-controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
  margin-left: auto;
}

/* ── Search bar ── */

.search-section {
  margin-top: 0.6rem;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border: 3px solid var(--border);
  padding: 0.4rem 0.65rem;
  background: var(--bg);
}

.search-box input {
  flex: 1;
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 1rem;
  font-weight: 600;
  background: transparent;
  color: var(--fg);
}

.search-box input::placeholder {
  color: #999;
  font-weight: 500;
}

.search-dropdown {
  display: none;
  position: absolute;
  top: 100%;
  left: -3px;
  right: -3px;
  border: 3px solid var(--border);
  border-top: none;
  background: var(--bg);
  max-height: 320px;
  overflow-y: auto;
  z-index: 30;
}

.search-dropdown.open {
  display: block;
}

.search-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.65rem;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 600;
  border-bottom: 1px solid var(--muted);
}

.search-item:hover,
.search-item.active {
  background: var(--muted);
}

.search-item .search-company {
  color: #666;
  font-weight: 400;
  font-size: 0.85rem;
}

.search-item .search-count {
  margin-left: auto;
  font-size: 0.78rem;
  color: var(--accent);
  font-weight: 700;
}

/* ── Ticker profile ── */

.ticker-profile {
  border: 3px solid var(--border);
  padding: 1rem;
  margin-top: 0.6rem;
  background: var(--bg);
}

.ticker-profile-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.ticker-profile-header h2 {
  margin: 0;
  font-size: 1.5rem;
  text-transform: uppercase;
}

.ticker-profile-header .muted {
  margin: 0;
}

.ticker-profile-back {
  margin-right: 0.5rem;
}

.ticker-profile .ticker-logo {
  width: 36px;
  height: 36px;
}

.ticker-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.ticker-metric {
  border: 2px solid var(--border);
  padding: 0.5rem;
  text-align: center;
}

.ticker-metric-value {
  display: block;
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 2px;
}

.ticker-metric-label {
  display: block;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #666;
}

.ticker-strategies-table {
  margin-top: 0.5rem;
}

.ticker-anomaly-summary {
  margin-top: 0.75rem;
  padding: 0.5rem;
  border: 2px solid var(--border);
  font-size: 0.92rem;
}

.ticker-anomaly-clean {
  color: #2a7d2a;
}

/* ── Category tabs ── */

.categories-section {
  margin-top: 0.6rem;
}

.category-tabs {
  display: flex;
  gap: 0;
  flex-wrap: wrap;
  border: 3px solid var(--border);
  background: var(--bg);
}

.category-tab {
  flex: 1;
  min-width: 0;
  padding: 0.55rem 0.6rem;
  border: none;
  border-right: 2px solid var(--border);
  background: var(--bg);
  color: var(--fg);
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  transition: background-color 0.15s linear, color 0.15s linear;
}

.category-tab:last-child {
  border-right: none;
}

.category-tab:hover {
  background: var(--muted);
}

.category-tab.active {
  background: var(--fg);
  color: var(--bg);
}

.category-story {
  margin: 0;
  padding: 0.5rem 0.65rem;
  border: 3px solid var(--border);
  border-top: none;
  background: var(--muted);
  font-size: 0.92rem;
  font-weight: 500;
  font-style: italic;
  min-height: 1.8rem;
}

/* ── Comparison view ── */

.comparison-view {
  border: 3px solid var(--border);
  padding: 1rem;
  margin-top: 0.6rem;
  background: #fffdf9;
}

.comparison-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.comparison-header h2 {
  margin: 0;
  font-size: 1.1rem;
  text-transform: uppercase;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.comparison-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.65rem;
  margin-bottom: 0.75rem;
}

.comparison-col {
  border: 2px solid var(--border);
  padding: 0.65rem;
  background: var(--bg);
}

.comparison-col h3 {
  margin: 0 0 0.15rem;
  font-size: 0.95rem;
  text-transform: uppercase;
}

.comparison-col .comparison-category {
  font-size: 0.78rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0 0 0.5rem;
}

.comparison-stat {
  display: flex;
  justify-content: space-between;
  font-size: 0.88rem;
  padding: 0.15rem 0;
  border-bottom: 1px solid var(--muted);
}

.comparison-stat-value {
  font-weight: 700;
}

.comparison-risk-bar {
  display: flex;
  height: 8px;
  border: 1px solid var(--border);
  margin: 0.4rem 0;
  overflow: hidden;
}

.comparison-risk-bar .bar-low {
  background: var(--bg);
}

.comparison-risk-bar .bar-med {
  background: #cfcfcf;
}

.comparison-risk-bar .bar-high {
  background: var(--accent);
}

.comparison-ticker {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.85rem;
  font-weight: 600;
  margin-right: 0.35rem;
}

.comparison-ticker.overlap {
  color: var(--accent);
}

.comparison-ticker.overlap::after {
  content: '●';
  font-size: 0.6rem;
}

.comparison-result {
  border-top: 2px solid var(--border);
  padding-top: 0.65rem;
  margin-top: 0.5rem;
}

.comparison-result h3 {
  margin: 0 0 0.35rem;
  font-size: 0.95rem;
  text-transform: uppercase;
}

.comparison-controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
}

/* ── Card summary stats ── */

.card-stats {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 0.45rem;
  padding: 0.4rem 0.5rem;
  border: 2px solid var(--border);
  background: var(--bg);
  font-size: 0.88rem;
}

.card-stat {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.card-stat-value {
  font-weight: 700;
}

.card-stat-label {
  color: #666;
  font-size: 0.82rem;
}

.card-risk-bar {
  display: flex;
  height: 6px;
  width: 60px;
  border: 1px solid var(--border);
  overflow: hidden;
}

.card-risk-bar .bar-low {
  background: var(--bg);
}

.card-risk-bar .bar-med {
  background: #cfcfcf;
}

.card-risk-bar .bar-high {
  background: var(--accent);
}

/* ── Clickable tickers ── */

.ticker-link {
  cursor: pointer;
  text-decoration: none;
  color: inherit;
}

.ticker-link:hover {
  text-decoration: underline;
  color: var(--accent);
}

/* ── Responsive: category tabs ── */

@media (max-width: 767px) {
  .category-tab {
    font-size: 0.72rem;
    padding: 0.4rem;
  }

  .site-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-controls {
    margin-left: 0;
  }

  .comparison-columns {
    grid-template-columns: 1fr;
  }

  .ticker-metrics-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

**Step 2: Remove stale CSS**

Remove these selectors/blocks from `styles.css`:
- `.hero`, `.hero h1`, `.hero-subtitle` (replaced by `.site-header`, `.site-title`)
- `.strategy-nav`, `.strategy-nav-title`, `.strategy-index`, `.strategy-index-item` (all 4 blocks + hover/active)
- `.usage-panel`, `.usage-panel h2`, `.usage-panel p`, `.usage-panel::before`, `.usage-steps`, `.usage-steps li, .usage-panel ul li` (all 6 blocks)
- `.drawer`, `.drawer.open`, `.drawer-head`, `.drawer-head h2`, `.drawer-body`, `.drawer-help`, `.mode-badge`, `.drawer-subtitle` (all 8 blocks)
- `.hero-meta` (moved to `.header-controls`)
- The `@media (max-width: 767px)` rule for `.hero` border-width

**Step 3: Commit**

```bash
git add frontend/styles.css
git commit -m "feat(frontend): update CSS for compact header, categories, search, comparison"
```

---

### Task 5: Update main.mjs — state, DOM refs, boot, and category tabs

Rewrite `main.mjs` to use the new DOM structure, add category filtering, and wire the search bar. Remove drawer logic.

**Files:**
- Modify: `frontend/main.mjs`

**Step 1: Rewrite `main.mjs`**

Replace the full file. Key changes:
- Import `CATEGORIES, categoryForStrategy, categoryMetrics` from `categories.mjs`
- Import `buildTickerIndex` from `data.mjs`
- New state fields: `activeCategory: 'todos'`, `tickerIndex: new Map()`, `comparedStrategies: new Set()`
- Remove: `selectedStrategies`, `mode` (moved into comparison view)
- New DOM refs: `categoryTabs`, `categoryStory`, `tickerSearch`, `searchResults`, `tickerProfile`, `comparisonView`
- Remove DOM refs: `compareDrawer`, `compareList`, `compareResults`, `compareCount`, `modeHelp`, `modeBadge`, `resultsTitle`, `mode`, `closeCompare`
- `rebuildVisibleStrategies()` now filters by both sector AND active category
- New `renderCategoryTabs()` function
- New `handleSearch()` with autocomplete
- New `openTickerProfile(ticker)` and `closeTickerProfile()`
- New `openComparison()`, `closeComparison()`, `toggleCompareStrategy(id)`
- Boot calls `renderCategoryTabs()` after loading bundle

```javascript
import { buildStockMap, buildTickerSets, buildTickerIndex, loadBundle } from './js/data.mjs';
import { CATEGORIES, categoryForStrategy, categoryMetrics } from './js/categories.mjs';
import { formatGeneratedAt } from './js/datetime.mjs';
import { intersectAndOr } from './js/intersections.mjs';
import {
  renderConsensusPicks,
  renderIntelligence,
  renderStrategies,
  renderComparison,
  renderTickerProfile,
} from './js/render.mjs';

const state = {
  bundle: null,
  visibleStrategies: [],
  activeCategory: 'todos',
  comparedStrategies: new Set(),
  comparisonMode: 'AND',
  displayLimit: 30,
  sectorFilter: 'ALL',
  tickerSets: {},
  stockMap: new Map(),
  fullStockMap: new Map(),
  tickerIndex: new Map(),
  activeStrategyId: null,
  activeTickerProfile: null,
};

const dom = {
  status: document.getElementById('status'),
  generatedAt: document.getElementById('generated-at'),
  universeCount: document.getElementById('universe-count'),
  sectorFilter: document.getElementById('sector-filter'),
  displayLimit: document.getElementById('display-limit'),
  categoryTabs: document.getElementById('category-tabs'),
  categoryStory: document.getElementById('category-story'),
  tickerSearch: document.getElementById('ticker-search'),
  searchResults: document.getElementById('search-results'),
  tickerProfile: document.getElementById('ticker-profile'),
  comparisonView: document.getElementById('comparison-view'),
  consensusPicks: document.getElementById('consensus-picks'),
  strategies: document.getElementById('strategies'),
  intelSection: document.getElementById('intelligence-section'),
  intelStats: document.getElementById('intel-stats'),
  intelHighBody: document.getElementById('intel-anomalies-body'),
  intelAllBody: document.getElementById('intel-all-body'),
  intelToggleAll: document.getElementById('intel-toggle-all'),
  intelAllWrap: document.getElementById('intel-all-wrap'),
  intelAnomaliesWrap: document.getElementById('intel-anomalies-wrap'),
};

function stockSector(stock) {
  const raw = stock?.Setor;
  if (typeof raw === 'string' && raw.trim()) return raw.trim();
  return 'Setor não informado';
}

function rebuildVisibleStrategies() {
  if (!state.bundle) {
    state.visibleStrategies = [];
    return;
  }

  const catDef = CATEGORIES.find((c) => c.id === state.activeCategory);
  const allowedIds = catDef && catDef.strategies.length > 0 ? new Set(catDef.strategies) : null;

  state.visibleStrategies = state.bundle.strategies
    .filter((strategy) => !allowedIds || allowedIds.has(strategy.strategy_id))
    .map((strategy) => {
      const scopedStocks =
        state.sectorFilter === 'ALL'
          ? strategy.stocks
          : strategy.stocks.filter((stock) => stockSector(stock) === state.sectorFilter);
      return { ...strategy, stocks: scopedStocks };
    });
}

function rebuildDerivedData() {
  state.tickerSets = buildTickerSets(state.visibleStrategies, state.displayLimit);
  state.stockMap = buildStockMap(state.visibleStrategies, state.displayLimit);
}

function rebuildViewData() {
  rebuildVisibleStrategies();
  rebuildDerivedData();
}

function limitLabel() {
  return state.displayLimit === 'ALL' ? 'todos' : `top ${state.displayLimit}`;
}

function renderSectorFilterOptions() {
  if (!dom.sectorFilter || !state.bundle) return;
  const sectors = new Set();
  for (const strategy of state.bundle.strategies) {
    for (const stock of strategy.stocks) {
      sectors.add(stockSector(stock));
    }
  }

  const options = ['ALL', ...[...sectors].sort((a, b) => a.localeCompare(b, 'pt-BR'))];
  dom.sectorFilter.innerHTML = '';
  for (const value of options) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value === 'ALL' ? 'Todos' : value;
    option.selected = value === state.sectorFilter;
    dom.sectorFilter.appendChild(option);
  }
}

function renderCategoryTabs() {
  if (!dom.categoryTabs) return;
  dom.categoryTabs.innerHTML = '';
  for (const cat of CATEGORIES) {
    const btn = document.createElement('button');
    btn.className = `category-tab${cat.id === state.activeCategory ? ' active' : ''}`;
    btn.dataset.categoryId = cat.id;
    btn.innerHTML = `<i data-lucide="${cat.icon}"></i> ${cat.label}`;
    btn.addEventListener('click', () => {
      state.activeCategory = cat.id;
      renderCategoryTabs();
      rebuildViewData();
      renderPage();
    });
    dom.categoryTabs.appendChild(btn);
  }

  if (dom.categoryStory) {
    const catDef = CATEGORIES.find((c) => c.id === state.activeCategory);
    dom.categoryStory.textContent = catDef?.story || '';
    dom.categoryStory.style.display = catDef?.story ? '' : 'none';
  }

  if (window.lucide?.createIcons) window.lucide.createIcons();
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const temp = document.createElement('textarea');
  temp.value = text;
  temp.setAttribute('readonly', '');
  temp.style.position = 'absolute';
  temp.style.left = '-9999px';
  document.body.appendChild(temp);
  temp.select();
  document.execCommand('copy');
  document.body.removeChild(temp);
}

function openTickerProfile(ticker) {
  if (!dom.tickerProfile || !state.tickerIndex.has(ticker)) return;
  state.activeTickerProfile = ticker;
  dom.tickerProfile.style.display = '';
  renderTickerProfile(
    dom.tickerProfile,
    state.tickerIndex.get(ticker),
    state.bundle?.intelligence,
    () => closeTickerProfile(),
    (t) => openTickerProfile(t)
  );
}

function closeTickerProfile() {
  state.activeTickerProfile = null;
  if (dom.tickerProfile) {
    dom.tickerProfile.style.display = 'none';
    dom.tickerProfile.innerHTML = '';
  }
}

function handleSearch() {
  const query = dom.tickerSearch.value.trim().toUpperCase();
  if (query.length < 1) {
    dom.searchResults.classList.remove('open');
    return;
  }

  const matches = [];
  for (const [ticker, entry] of state.tickerIndex) {
    if (matches.length >= 12) break;
    if (ticker.includes(query) || entry.company.toUpperCase().includes(query)) {
      matches.push(entry);
    }
  }

  if (matches.length === 0) {
    dom.searchResults.classList.remove('open');
    return;
  }

  dom.searchResults.innerHTML = matches
    .map(
      (entry) => `
      <div class="search-item" data-ticker="${entry.ticker}">
        <span>${entry.ticker}</span>
        <span class="search-company">${entry.company}</span>
        <span class="search-count">${entry.appearances.length} estratégias</span>
      </div>
    `
    )
    .join('');
  dom.searchResults.classList.add('open');

  dom.searchResults.querySelectorAll('.search-item').forEach((el) => {
    el.addEventListener('click', () => {
      openTickerProfile(el.dataset.ticker);
      dom.searchResults.classList.remove('open');
      dom.tickerSearch.value = '';
    });
  });
}

function openComparison() {
  if (!dom.comparisonView) return;
  dom.comparisonView.style.display = '';
  refreshComparison();
}

function closeComparison() {
  state.comparedStrategies.clear();
  if (dom.comparisonView) {
    dom.comparisonView.style.display = 'none';
    dom.comparisonView.innerHTML = '';
  }
}

function refreshComparison() {
  if (!dom.comparisonView || state.comparedStrategies.size === 0) return;

  const ids = [...state.comparedStrategies];
  const strategies = ids
    .map((id) => state.visibleStrategies.find((s) => s.strategy_id === id))
    .filter(Boolean);

  const sets = ids.map((id) => state.tickerSets[id]).filter(Boolean);
  const resultSet = intersectAndOr(state.comparisonMode, sets);
  const resultTickers = [...resultSet];

  renderComparison(
    dom.comparisonView,
    strategies,
    state.comparisonMode,
    resultTickers,
    state.stockMap,
    state.fullStockMap,
    state.displayLimit,
    (newMode) => {
      state.comparisonMode = newMode;
      refreshComparison();
    },
    () => closeComparison(),
    (ticker) => openTickerProfile(ticker)
  );
}

function renderPage() {
  if (!state.bundle) return;

  const consensus = [...state.stockMap.values()]
    .map((entry) => ({
      ticker: entry.ticker,
      count: entry.strategies.length,
      strategies: entry.strategies,
      sample: entry.sample,
    }))
    .sort((a, b) => b.count - a.count || a.ticker.localeCompare(b.ticker))
    .slice(0, 12);
  renderConsensusPicks(
    dom.consensusPicks,
    consensus,
    state.bundle.strategies.length,
    state.bundle?.intelligence,
    (ticker) => openTickerProfile(ticker)
  );

  if (dom.intelSection && state.bundle?.intelligence) {
    renderIntelligence(dom.intelSection, dom.intelStats, dom.intelHighBody, dom.intelAllBody, state.bundle.intelligence);
  }

  renderStrategies(
    dom.strategies,
    state.visibleStrategies,
    state.activeStrategyId,
    state.displayLimit,
    (strategyId) => {
      state.activeStrategyId = state.activeStrategyId === strategyId ? null : strategyId;
      renderPage();
    },
    () => {
      state.activeStrategyId = null;
      renderPage();
    },
    (strategyId) => {
      if (state.comparedStrategies.has(strategyId)) {
        state.comparedStrategies.delete(strategyId);
      } else if (state.comparedStrategies.size < 4) {
        state.comparedStrategies.add(strategyId);
      }
      if (state.comparedStrategies.size === 0) {
        closeComparison();
      } else {
        openComparison();
      }
      renderPage();
    },
    async (strategyId) => {
      const strategy = state.visibleStrategies.find((item) => item.strategy_id === strategyId);
      if (!strategy) return false;
      const maxRows = state.displayLimit === 'ALL' ? strategy.stocks.length : Number(state.displayLimit);
      const tickers = strategy.stocks
        .slice(0, maxRows)
        .map((stock) => stock?.Papel)
        .filter((ticker) => typeof ticker === 'string' && ticker.length > 0);

      if (!tickers.length) {
        dom.status.textContent = `Sem ativos para copiar em ${strategy.name} com o filtro atual.`;
        return false;
      }

      try {
        await copyText(tickers.join('\n'));
        dom.status.textContent = `${tickers.length} ticker(s) copiados de ${strategy.name}.`;
        return true;
      } catch {
        dom.status.textContent = `Falha ao copiar Top N de ${strategy.name}.`;
        return false;
      }
    },
    state.bundle?.intelligence,
    state.comparedStrategies,
    (ticker) => openTickerProfile(ticker)
  );
}

async function boot() {
  try {
    dom.status.textContent = 'Carregando...';
    const bundle = await loadBundle('./data/strategies.bundle.json');
    state.bundle = bundle;
    state.fullStockMap = buildStockMap(bundle.strategies, 'ALL');
    state.tickerIndex = buildTickerIndex(bundle.strategies);
    rebuildViewData();
    renderSectorFilterOptions();
    renderCategoryTabs();

    dom.generatedAt.textContent = formatGeneratedAt(bundle.generated_at);
    dom.universeCount.textContent = String(state.fullStockMap.size);
    dom.status.textContent = `${bundle.strategy_count ?? bundle.strategies.length} estratégias carregadas.`;
    renderPage();
  } catch (error) {
    dom.status.textContent = `Erro: ${error.message}. Rode \`just crawl\` para gerar o bundle.`;
  }
}

if (dom.displayLimit) {
  dom.displayLimit.value = String(state.displayLimit);
  dom.displayLimit.addEventListener('change', (event) => {
    const raw = event.target.value;
    state.displayLimit = raw === 'ALL' ? 'ALL' : Number(raw);
    rebuildDerivedData();
    dom.universeCount.textContent = String(state.fullStockMap.size);
    renderPage();
    if (state.comparedStrategies.size > 0) refreshComparison();
  });
}

if (dom.sectorFilter) {
  dom.sectorFilter.addEventListener('change', (event) => {
    state.sectorFilter = event.target.value;
    rebuildViewData();
    renderPage();
    if (state.comparedStrategies.size > 0) refreshComparison();
  });
}

if (dom.tickerSearch) {
  dom.tickerSearch.addEventListener('input', handleSearch);
  dom.tickerSearch.addEventListener('focus', handleSearch);
  document.addEventListener('click', (event) => {
    if (!dom.tickerSearch.contains(event.target) && !dom.searchResults.contains(event.target)) {
      dom.searchResults.classList.remove('open');
    }
  });
}

if (dom.intelToggleAll) {
  dom.intelToggleAll.addEventListener('click', () => {
    const wrap = dom.intelAllWrap;
    if (!wrap) return;
    const isHidden = wrap.style.display === 'none';
    wrap.style.display = isHidden ? '' : 'none';
    const label = dom.intelToggleAll.querySelector('span');
    if (label) label.textContent = isHidden ? 'Ocultar médias e baixas' : 'Mostrar médias e baixas';
  });
}

boot();
```

Note the new parameters added to `renderStrategies` and `renderConsensusPicks` calls — these will be implemented in the next task.

**Step 2: Commit**

```bash
git add frontend/main.mjs
git commit -m "feat(frontend): rewrite main.mjs for categories, search, comparison"
```

---

### Task 6: Update render.mjs — enhanced strategy cards + new render functions

Add summary stats to strategy cards, implement `renderComparison`, `renderTickerProfile`, make tickers clickable, update function signatures.

**Files:**
- Modify: `frontend/js/render.mjs`

This is the largest task. Key changes:

**6a: Add card summary stats to `renderStrategies`**

In the `renderStrategies` function, after the card description and before the top picks line, add a `.card-stats` div showing:
- Stock count (`filtered_size → result_size`)
- Two category-specific avg metrics (computed from the strategy's visible stocks)
- Risk distribution mini-bar

Add new parameters to `renderStrategies`: `comparedStrategies` (Set) and `onTickerClick` (callback).

Update the "Interseção" button text to "Comparar" and add an `.active` class when the strategy is in `comparedStrategies`.

**6b: Make tickers clickable**

Wherever a ticker is rendered (consensus picks, strategy tables, intersection results), wrap it in a `<span class="ticker-link" data-ticker="XXX">` and attach click listeners that call `onTickerClick(ticker)`.

Update `renderConsensusPicks` to accept `onTickerClick` as 5th parameter.

**6c: Add `renderComparison` function**

New export that renders the full-width comparison view:

```javascript
export function renderComparison(
  container,
  strategies,
  mode,
  resultTickers,
  stockMap,
  fullStockMap,
  displayLimit,
  onModeChange,
  onClose,
  onTickerClick
)
```

It renders:
- Header with title + close button
- One column per strategy (max 4) showing: name, category label, stock count, avg DY/P/L/ROIC, risk bar, top 5 tickers with overlap markers
- Bottom: intersection/union result with AND/OR select, ticker count, copy button

**6d: Add `renderTickerProfile` function**

New export:

```javascript
export function renderTickerProfile(container, tickerEntry, intelligence, onClose, onTickerClick)
```

It renders:
- Back button + logo + ticker + company + sector
- Source links
- Metrics grid (P/L, P/VP, DY, ROIC, Marg. EBIT, Risk level)
- Strategy appearances table (strategy name, rank, category)
- Anomaly summary

The exact implementation code is long — the implementer should follow the wireframes from the design doc and use existing helper functions (`logoMarkup`, `sourceLinksMarkup`, `anomalyBadge`, `evaluateRisk`, `asNumber`, `getPathValue`, `computeRiskProfile`).

Import `categoryForStrategy` from `categories.mjs` at the top of `render.mjs`.

**Step 1: Implement all changes in `render.mjs`**

**Step 2: Verify page loads and all features work**

Run: `python3 -m http.server -d frontend 8000` — test in browser:
- Category tabs filter strategies
- Strategy cards show summary stats + risk bars
- Search autocompletes and opens ticker profiles
- Comparar button adds strategies to comparison view
- Tickers are clickable everywhere

**Step 3: Commit**

```bash
git add frontend/js/render.mjs
git commit -m "feat(frontend): enhanced cards, comparison view, ticker profile, clickable tickers"
```

---

### Task 7: Update existing tests + add integration test

Update existing test imports if needed, add a basic test for the new render functions.

**Files:**
- Modify: `frontend/tests/intersections.test.mjs` (if imports changed)
- Modify: `frontend/tests/risk.test.mjs` (if imports changed)
- Create: `frontend/tests/render.test.mjs`

**Step 1: Write render smoke tests**

Test that the new exported functions exist and don't throw when given minimal inputs. Since `render.mjs` uses DOM APIs, these tests use a minimal JSDOM-like stub or just test the non-DOM helpers.

```javascript
// frontend/tests/render.test.mjs
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

// We can only test non-DOM helpers without a full browser env
// Just verify module imports work
describe('render module', () => {
  it('exports all required functions', async () => {
    const mod = await import('../js/render.mjs');
    assert.equal(typeof mod.renderStrategies, 'function');
    assert.equal(typeof mod.renderConsensusPicks, 'function');
    assert.equal(typeof mod.renderIntelligence, 'function');
    assert.equal(typeof mod.renderComparison, 'function');
    assert.equal(typeof mod.renderTickerProfile, 'function');
  });
});
```

**Step 2: Run all tests**

Run: `node --test frontend/tests/*.test.mjs`
Expected: All pass

**Step 3: Commit**

```bash
git add frontend/tests/
git commit -m "test(frontend): add render module export test, update test suite"
```

---

### Task 8: Final cleanup + verify

**Files:**
- Possibly modify: `frontend/styles.css` (tweaks)
- Possibly modify: `frontend/js/render.mjs` (tweaks)

**Step 1: Run linter**

Run: `just check`
Expected: All checks passed (Python side unchanged)

**Step 2: Run all frontend tests**

Run: `node --test frontend/tests/*.test.mjs`
Expected: All pass

**Step 3: Manual browser verification**

Serve: `python3 -m http.server -d frontend 8000`

Verify:
1. Compact header shows title + controls in one line
2. Search bar autocompletes tickers, opens profile on click
3. Ticker profile shows metrics, strategy appearances, anomaly summary, back button works
4. Category tabs filter strategies, story text updates
5. Strategy cards show summary stats (avg metrics, risk bar)
6. "Comparar" button adds to comparison view (max 4)
7. Comparison view shows columns, overlap markers, AND/OR toggle
8. Consensus picks appear below strategies
9. Intelligence section shows at bottom
10. All tickers are clickable throughout the UI
11. Responsive: works on narrow viewport (767px)

**Step 4: Fix any issues found**

**Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix(frontend): polish UX improvements after manual review"
```

Plan complete and saved to `docs/plans/2026-03-27-frontend-ux-improvements-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?