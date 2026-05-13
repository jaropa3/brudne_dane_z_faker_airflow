# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Local runner (no UI, no scheduler — for debugging)
python main.py

# Dagster: dev UI on http://localhost:3000
dagster dev

# Materialize a single asset from CLI
dagster asset materialize --select validated_orders -m defs.orders_etl

# Run all tests
pytest tests/

# Install dependencies
pip install -r requirements.txt
```

## Architecture

Python ETL pipeline: CSV files → validate → PostgreSQL (staging → core tables).

**Flow:**
```
CSV files (data/raw_data/)
  → src/extract.py   load_csv()                       — encoding/separator detection
  → src/validate.py  validate()                        — returns (valid_df, quarantine_df, duplicates_df)
  → src/copy_io.py   copy_from_file() / copy_from_df()— COPY FROM STDIN → staging
  → src/load.py      insert_from_staging_to_core()    — staging → core with FK checks
```

The whole DB load (truncate staging, COPY into staging, insert from staging to core,
insert raw products file) runs inside a single SQLAlchemy transaction in
`load_phase` ([main.py](main.py)). All DB-touching functions take a `Connection`,
not an `Engine`.

**Key modules:**
- `src/load.py` — config loading, quarantine saves (Excel), DB insert functions, staging truncate
- `src/extract.py` — CSV ingestion with auto-encoding/separator detection via `chardet`
- `src/validate.py` — validates orders: type casting, null checks, date parsing (5 formats), status whitelist, future-date check, duplicate detection. Public entry: `validate(df)`. Internal helpers: `_cast_types`, `_parse_dates`, `_split_duplicates`, `_apply_rules`.
- `src/connection.py` — SQLAlchemy engine via env vars (`DB_USER`, `DB_PASSWORD`) + `src/config.yaml` (host/port/dbname)
- `src/copy_io.py` — bulk PostgreSQL COPY via the DBAPI cursor of the supplied SQLAlchemy connection. Table name parameterised with `psycopg2.sql.Identifier`.
- `src/logger_app.py` — JSON-structured logger; `setup_logger("src")` is called once in `main()` and configures handlers on the `src` logger. Modules use `logging.getLogger(__name__)` and propagate to it.
- `src/step.py` — `@step("name")` decorator: logs `step.start`/`step.ok`/`step.fail` with `duration_s`. Used in `main.py` to wrap each phase.

**Database tables:**
- Staging: `stag_orders`, `stag_customers`, `stag_products` — truncated at the start of each load
- Core: `orders`, `customers`, `products` — inserted with `ON CONFLICT DO NOTHING`
- `rejected_orders` — orders that fail FK checks (missing product or customer); `order_id` is `UNIQUE` so re-runs use `ON CONFLICT DO NOTHING`
- `raw_products_files` — raw text backup of products CSV, deduplicated by SHA-256

**validate() details:**
- Raises `ValueError` if any required column is missing (`order_id`, `customer_id`, `product_id`, `quantity`, `amount`, `order_date`, `status`)
- Accepts 5 date formats: `%Y-%m-%d`, `%d/%m/%Y`, `%m/%d/%Y`, `%d.%m.%Y`, `%Y%m%d`
- All timestamps are tz-naive throughout the module (parsed and `now()` alike) to avoid mixed-tz comparison errors
- Valid statuses: `pending`, `paid`, `refunded`, `cancelled`
- Duplicate `order_id`: keeps last by `order_date`; earlier copies go to `duplicates_df`
- Quarantined rows get `fail_*` boolean columns explaining the reason (e.g. `fail_positive_qty`, `fail_valid_status`, `fail_not_future_date`)

**Config & credentials:**
- `src/config.yaml` — DB host/port/dbname, file paths, quarantine output dir
- `.env` must provide `DB_USER` and `DB_PASSWORD`

**Orchestration (Dagster):**
- `defs/orders_etl.py` — asset-based pipeline (`raw_orders` → `validated_orders` → `core_tables_loaded`) + daily schedule (`0 6 * * *`, Europe/Warsaw).
- `pyproject.toml` declares the Dagster code location (`module_name = "defs.orders_etl"`), so `dagster dev` works with no flags.
- `src/` functions are unchanged from the standalone runner — Dagster assets are thin wrappers around them. `main.py` is kept as a no-UI local runner.

**Imports & testing:**
- `src/` is a Python package (has `__init__.py`). Internal imports inside `src/` use relative form (`from .logger_app import …`).
- External callers (`main.py`, tests) use absolute (`from src.validate import validate`).
- `pytest.ini` sets `pythonpath = .` so the project root is on `sys.path`.
