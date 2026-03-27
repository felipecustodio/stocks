# Frontend Screening Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static, strategy-first frontend (pt-BR) that explores screening results, compares strategies with dynamic AND/OR intersections, and shows rule-based stock risk warnings, backed by enriched strategy JSON outputs plus a generated frontend bundle.

**Architecture:** Extend each screening pipeline output to a unified metadata contract (`strategy + context + stocks`) while preserving strategy-specific ranking fields. Add a post-crawl bundler that auto-discovers valid strategy outputs and produces `frontend/data/strategies.bundle.json`. Replace the current simple HTML table with a Swiss-style static app (vanilla ES modules) that reads the bundle, renders editorial strategy cards, provides a comparison drawer, and computes risk/intersections client-side.

**Tech Stack:** Python (Scrapy pipelines, pytest), static frontend (HTML/CSS/vanilla ES modules), Node built-in test runner (`node --test`) for frontend pure-logic tests.

---

## File Structure (Planned)

- Modify: `stocks/pipelines.py`
  - Responsibility: enrich strategy outputs with standardized metadata and counts.
- Modify: `stocks/spiders/fundamentus.py`
  - Responsibility: provide crawl timestamp/context used by output metadata (if needed).
- Create: `stocks/bundle.py`
  - Responsibility: discover strategy JSON files, validate schema, generate frontend bundle.
- Modify: `justfile`
  - Responsibility: add `bundle` command and ensure crawl flow can generate bundle.
- Modify: `.gitignore`
  - Responsibility: ignore generated frontend bundle file.
- Create: `tests/test_strategy_output_schema.py`
  - Responsibility: verify each strategy output contract.
- Create: `tests/test_bundle_builder.py`
  - Responsibility: verify bundle generation and index consistency.
- Modify: `frontend/index.html`
  - Responsibility: app shell/layout in pt-BR using Swiss visual rules.
- Create: `frontend/styles.css`
  - Responsibility: centralized design tokens/patterns/components styling.
- Create: `frontend/main.mjs`
  - Responsibility: app bootstrap and state orchestration.
- Create: `frontend/js/data.mjs`
  - Responsibility: load/validate bundle and expose query helpers.
- Create: `frontend/js/intersections.mjs`
  - Responsibility: deterministic AND/OR set operations.
- Create: `frontend/js/risk.mjs`
  - Responsibility: rule-based risk score + flags.
- Create: `frontend/js/render.mjs`
  - Responsibility: render strategy cards, stock cards, drawers, and states.
- Create: `frontend/tests/intersections.test.mjs`
  - Responsibility: intersection unit tests.
- Create: `frontend/tests/risk.test.mjs`
  - Responsibility: risk engine unit tests.
- Modify: `README.md`
  - Responsibility: document new crawl->bundle->frontend workflow.

### Task 1: Define Strategy Output Contract in Pipelines

**Files:**
- Modify: `stocks/pipelines.py`
- Test: `tests/test_strategy_output_schema.py`

- [ ] **Step 1: Write failing schema tests for strategy JSON outputs**

```python
# tests/test_strategy_output_schema.py
REQUIRED_TOP_LEVEL = {
    "strategy_id", "name", "description", "methodology_summary",
    "use_cases", "caveats", "generated_at",
    "universe_size", "filtered_size", "result_size", "stocks",
}

def test_strategy_output_has_required_top_level_fields(tmp_path):
    payload = {"strategy_id": "magicformula"}
    missing = REQUIRED_TOP_LEVEL - payload.keys()
    assert not missing
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_strategy_output_schema.py -v`
Expected: FAIL showing missing required fields.

- [ ] **Step 3: Implement minimal metadata framework in pipelines**

```python
class ScreeningPipeline:
    strategy_id: str
    strategy_name: str
    strategy_description: str
    methodology_summary: str
    use_cases: list[str]
    caveats: list[str]

    def build_output(self, spider, filtered, ranked):
        return {
            "strategy_id": self.strategy_id,
            "name": self.strategy_name,
            "description": self.strategy_description,
            "methodology_summary": self.methodology_summary,
            "use_cases": self.use_cases,
            "caveats": self.caveats,
            "generated_at": dt.datetime.now(dt.UTC).isoformat(),
            "universe_size": len(self.items),
            "filtered_size": len(filtered),
            "result_size": len(ranked),
            "stocks": ranked,
        }
```

Apply metadata fields for every strategy subclass.

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_strategy_output_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add stocks/pipelines.py tests/test_strategy_output_schema.py
git commit -m "feat: standardize strategy output schema with metadata"
```

### Task 2: Write Strategy Metadata Content for All Pipelines

**Files:**
- Modify: `stocks/pipelines.py`
- Test: `tests/test_strategy_output_schema.py`

- [ ] **Step 1: Write failing tests for metadata quality**

```python
def test_use_cases_and_caveats_are_non_empty_lists(strategy_payload):
    assert isinstance(strategy_payload["use_cases"], list) and strategy_payload["use_cases"]
    assert isinstance(strategy_payload["caveats"], list) and strategy_payload["caveats"]


def test_description_fields_are_non_blank(strategy_payload):
    for field in ["name", "description", "methodology_summary"]:
        assert strategy_payload[field].strip()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_strategy_output_schema.py -v`
Expected: FAIL on blank/missing metadata for at least one strategy.

- [ ] **Step 3: Fill per-strategy metadata definitions**

Add explicit strategy docs fields for all pipelines:
- `MagicFormulaPipeline`
- `CDVPipeline`
- `IntersectionPipeline`
- `GrahamNumberPipeline`
- `BazinPipeline`
- `QualityPipeline`
- `PiotroskiPipeline`
- `MultiFactorPipeline`
- `AcquirersMultiplePipeline`
- `DeepValuePipeline`
- `NetNetPipeline`
- `GARPPipeline`
- `MomentumValuePipeline`
- `ContrarianPipeline`
- `CashRichPipeline`

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_strategy_output_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add stocks/pipelines.py tests/test_strategy_output_schema.py
git commit -m "feat: add contextual metadata for all screening strategies"
```

### Task 3: Add Bundle Builder for Frontend

**Files:**
- Create: `stocks/bundle.py`
- Modify: `justfile`
- Modify: `.gitignore`
- Test: `tests/test_bundle_builder.py`

- [ ] **Step 1: Write failing tests for bundling behavior**

```python
def test_bundle_includes_only_valid_strategy_files(tmp_path):
    # write valid + invalid json files, run builder
    bundle = build_bundle(input_dir=tmp_path)
    assert len(bundle["strategies"]) == 1


def test_bundle_builds_stock_index(tmp_path):
    bundle = build_bundle(input_dir=tmp_path)
    assert bundle["stock_index"]["PETR4"] == ["magicformula", "quality"]
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_bundle_builder.py -v`
Expected: FAIL because bundler does not exist.

- [ ] **Step 3: Implement bundler**

```python
# stocks/bundle.py
def build_bundle(input_dir: Path, output_file: Path) -> dict:
    # discover *.json
    # keep payloads containing required strategy keys
    # sort strategies by name for stable output
    # create stock_index[ticker] -> [strategy_id, ...]
    # write frontend/data/strategies.bundle.json
```

Add CLI entry point:
`uv run python -m stocks.bundle --input . --output frontend/data/strategies.bundle.json`

- [ ] **Step 4: Wire commands**

- Add `bundle` target to `justfile`.
- Update `crawl` to run spider then bundler.
- Add `frontend/data/strategies.bundle.json` to `.gitignore`.

- [ ] **Step 5: Run tests to verify pass**

Run: `uv run pytest tests/test_bundle_builder.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add stocks/bundle.py tests/test_bundle_builder.py justfile .gitignore
git commit -m "feat: add strategy bundle generator for static frontend"
```

### Task 4: Build Frontend Data and Domain Modules (TDD)

**Files:**
- Create: `frontend/js/data.mjs`
- Create: `frontend/js/intersections.mjs`
- Create: `frontend/js/risk.mjs`
- Test: `frontend/tests/intersections.test.mjs`
- Test: `frontend/tests/risk.test.mjs`

- [ ] **Step 1: Write failing intersection tests**

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';
import { intersectAndOr } from '../js/intersections.mjs';

test('AND returns only common tickers', () => {
  const out = intersectAndOr('AND', [new Set(['A','B']), new Set(['B','C'])]);
  assert.deepEqual([...out], ['B']);
});
```

- [ ] **Step 2: Write failing risk tests**

```javascript
import { evaluateRisk } from '../js/risk.mjs';

test('high debt and low liquidity produces ALTO', () => {
  const risk = evaluateRisk(stockFixture);
  assert.equal(risk.risk_level, 'ALTO');
  assert.ok(risk.risk_flags.includes('endividamento_alto'));
});
```

- [ ] **Step 3: Run tests to verify failure**

Run:
- `node --test frontend/tests/intersections.test.mjs`
- `node --test frontend/tests/risk.test.mjs`

Expected: FAIL (missing modules/functions).

- [ ] **Step 4: Implement minimal modules**

- `intersections.mjs`: pure AND/OR set operations.
- `risk.mjs`: deterministic scoring + flags + `BAIXO/MÉDIO/ALTO` mapping.
- `data.mjs`: bundle load, schema check, strategy/ticker lookup helpers.

- [ ] **Step 5: Run tests to verify pass**

Run:
- `node --test frontend/tests/intersections.test.mjs`
- `node --test frontend/tests/risk.test.mjs`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/js/data.mjs frontend/js/intersections.mjs frontend/js/risk.mjs frontend/tests/intersections.test.mjs frontend/tests/risk.test.mjs
git commit -m "feat: add frontend domain modules for bundle, intersections, and risk"
```

### Task 5: Implement Swiss-Style Strategy-First UI Shell

**Files:**
- Modify: `frontend/index.html`
- Create: `frontend/styles.css`
- Create: `frontend/main.mjs`

- [ ] **Step 1: Write failing UI smoke assertions (minimal)**

Create a simple DOM smoke script (or extend README manual smoke checklist) to assert:
- strategy container exists
- compare drawer exists
- stock detail drawer exists

- [ ] **Step 2: Run smoke check to verify failure on old UI**

Run: `node frontend/tests/ui-smoke.mjs` (or equivalent script)
Expected: FAIL due missing structure.

- [ ] **Step 3: Implement app shell + tokens**

- Replace Bulma dependency with local styles.
- Add Swiss tokens and patterns in `styles.css`.
- Build layout in `index.html` (manifesto strip + strategy card list + drawers).
- Bootstrap app state/events in `main.mjs`.

- [ ] **Step 4: Run smoke check**

Run: `node frontend/tests/ui-smoke.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/styles.css frontend/main.mjs frontend/tests/ui-smoke.mjs
git commit -m "feat: implement strategy-first Swiss-style frontend shell"
```

### Task 6: Render Strategy Cards, Compare Drawer, and Stock Detail Drawer

**Files:**
- Create: `frontend/js/render.mjs`
- Modify: `frontend/main.mjs`
- Modify: `frontend/styles.css`

- [ ] **Step 1: Write failing behavior tests for drawer flows**

Add tests for:
- opening compare drawer from strategy card
- selecting strategies and switching `AND/OR`
- rendering intersection stock list
- opening stock detail with expanded risk flags

- [ ] **Step 2: Run tests to verify failure**

Run: `node --test frontend/tests/*.test.mjs`
Expected: FAIL on missing render wiring.

- [ ] **Step 3: Implement rendering and interactions**

- Render strategy metadata in cards (`description`, `use_cases`, `caveats`, counts).
- Add `Comparar` action opening right drawer with strategy selection.
- Compute intersections using `intersections.mjs`.
- Render stock cards with small risk badge.
- Open stock detail drawer with full rule breakdown.

- [ ] **Step 4: Run tests to verify pass**

Run: `node --test frontend/tests/*.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/js/render.mjs frontend/main.mjs frontend/styles.css frontend/tests
git commit -m "feat: add comparison drawer and detailed risk workflow"
```

### Task 7: End-to-End Data Flow Verification and Documentation

**Files:**
- Modify: `README.md`
- Modify: `justfile` (if needed after integration)

- [ ] **Step 1: Write/update failing documentation checks**

Add/update commands section expectations:
- `just crawl` generates strategy outputs + bundle
- local static serve instructions for frontend

- [ ] **Step 2: Run integration commands**

Run:
- `just crawl`
- `uv run pytest tests/test_strategy_output_schema.py tests/test_bundle_builder.py -v`
- `node --test frontend/tests/*.test.mjs`

Expected: all pass and bundle exists at `frontend/data/strategies.bundle.json`.

- [ ] **Step 3: Update README with final workflow**

Include:
- generation flow
- frontend usage
- risk model transparency note
- limitations/caveats

- [ ] **Step 4: Final verification**

Run: `just check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md justfile
git commit -m "docs: document screening explorer workflow and verification"
```

## Final Verification Checklist

- [ ] All strategy outputs contain required metadata and `stocks`
- [ ] Bundle generation succeeds and output schema is valid
- [ ] Frontend loads only bundle and renders strategy-first cards in pt-BR
- [ ] Compare drawer supports dynamic `AND`/`OR` intersections
- [ ] Risk badge + detailed risk breakdown render correctly
- [ ] Python + frontend tests pass
- [ ] Accessibility basics validated (focus states, keyboard access, contrast)

