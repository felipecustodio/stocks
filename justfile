# Install dependencies
sync:
    uv sync

# Update lockfile
lock:
    uv lock

# Run the Fundamentus spider (outputs data/raw/fundamentus.json + data/strategies/*.json)
crawl:
    uv run scrapy crawl fundamentus
    uv run python -m stocks.bundle --input data/strategies --output frontend/data/strategies.bundle.json

bundle:
    uv run python -m stocks.bundle --input data/strategies --output frontend/data/strategies.bundle.json

# Preview frontend locally at http://localhost:8000/
preview:
    uv run python -m http.server 8000 --directory frontend

# Cross-validate Fundamentus data against StatusInvest (run after crawl)
crossval:
    uv run scrapy crawl statusinvest

# Cross-validate specific tickers only
crossval-tickers tickers:
    uv run scrapy crawl statusinvest -a tickers={{tickers}}

# Lint with ruff
lint:
    uv run ruff check .

# Fix lint issues
lint-fix:
    uv run ruff check --fix .

# Format code
fmt:
    uv run ruff format .

# Type check with ty
typecheck:
    uv run ty check

# Run all checks
check: lint typecheck
