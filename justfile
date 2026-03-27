# Install dependencies
sync:
    uv sync

# Update lockfile
lock:
    uv lock

# Run the Fundamentus spider (outputs fundamentus.json, magicformula.json, cdv.json, intersection.json)
crawl:
    uv run scrapy crawl fundamentus
    uv run python -m stocks.bundle --input . --output frontend/data/strategies.bundle.json

bundle:
    uv run python -m stocks.bundle --input . --output frontend/data/strategies.bundle.json

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
