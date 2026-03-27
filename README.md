# Stocks Screening Explorer

Sistema de triagem de ações do mercado brasileiro com Scrapy + frontend estático para comparar estratégias.

## Comandos principais

- `just sync`: instala dependências Python com `uv`.
- `just crawl`: executa o spider, gera os JSONs de estratégias em `data/strategies/` e também o bundle do frontend.
- `just bundle`: regenera apenas `frontend/data/strategies.bundle.json`.
- `just check`: roda lint (`ruff`) e type-check (`ty`).

## Saídas de dados

Cada estratégia gera um JSON próprio com metadados e lista de ativos (`stocks`), incluindo:

- `strategy_id`, `name`, `description`, `methodology_summary`
- `use_cases`, `caveats`
- `generated_at`
- `universe_size`, `filtered_size`, `result_size`
- `stocks`

Arquivos de estratégias são salvos em:

- `data/strategies/*.json`

Dados brutos do spider (feed Scrapy) são salvos em:

- `data/raw/fundamentus.json`

O bundle consolidado usado pelo frontend é gerado em:

- `frontend/data/strategies.bundle.json`

## Frontend

O frontend fica em `frontend/` e consome somente o bundle:

- `frontend/index.html`
- `frontend/main.mjs`
- `frontend/js/*.mjs`

## Estratégias no frontend

- O bundle é montado automaticamente a partir dos JSONs válidos em `data/strategies/`.
- Estratégias novas aparecem automaticamente no site após rodar `just crawl` (ou `just bundle`, se os JSONs já existirem).
- O frontend mostra todas as estratégias, mesmo quando alguma retorna `0` ativos no dia.

## Funcionalidades principais da UI

- Cards de estratégia com detalhe expandível.
- Tabela de ativos por estratégia com métricas-chave e risco.
- Filtro global por setor.
- Top N configurável (`10`, `20`, `30`, `50`, `100`, `ALL`).
- Botão `Copiar Top N` por estratégia.
- Lista rápida de estratégias (índice clicável com scroll).
- Interseção/união entre estratégias no drawer.
- Blocos colapsáveis para gráficos de risco e análise quantitativa por rank.

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
