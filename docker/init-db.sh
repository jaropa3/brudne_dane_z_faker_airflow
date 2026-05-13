#!/bin/bash
# Tworzy bazę airflow (metadata Airflow) obok domyślnej bazy ETL (postgres).
# Skrypt jest wykonywany przez official postgres image podczas pierwszego startu.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "CREATE DATABASE airflow;"
