# Stocks Screening Explorer

Sistema de triagem de ações do mercado brasileiro com Scrapy + frontend estático para comparar estratégias.

## Comandos principais

- `just sync`: instala dependências Python com `uv`.
- `just crawl`: executa o spider, gera os JSONs das estratégias e também o bundle do frontend.
- `just bundle`: regenera apenas `frontend/data/strategies.bundle.json`.
- `just check`: roda lint (`ruff`) e type-check (`ty`).

## Saídas de dados

Cada estratégia gera um JSON próprio com metadados e lista de ativos (`stocks`), incluindo:

- `strategy_id`, `name`, `description`, `methodology_summary`
- `use_cases`, `caveats`
- `generated_at`
- `universe_size`, `filtered_size`, `result_size`
- `stocks`

O bundle consolidado usado pelo frontend é gerado em:

- `frontend/data/strategies.bundle.json`

## Frontend

O frontend fica em `frontend/` e consome somente o bundle:

- `frontend/index.html`
- `frontend/main.mjs`
- `frontend/js/*.mjs`

Para visualizar localmente, rode um servidor estático na pasta do projeto (por exemplo):

```bash
python -m http.server 8000
```

Depois abra:

- `http://localhost:8000/frontend/`

## Risco por ativo

O frontend calcula risco por regras transparentes (sem ML):

- `liquidez_baixa`
- `endividamento_alto`
- `margem_ebit_fraca`
- `volatilidade_12m_alta`
- `sinais_incompletos`

Níveis exibidos: `BAIXO`, `MÉDIO`, `ALTO`.
