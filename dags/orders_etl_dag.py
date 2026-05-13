from __future__ import annotations

from pathlib import Path

import pendulum
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

# Baza projektu = katalog nad dags/  →  /opt/airflow  (Docker) lub katalog lokalny
PROJECT_ROOT = Path(__file__).parent.parent


@dag(
    dag_id="orders_etl",
    schedule="0 6 * * *",
    start_date=pendulum.datetime(2026, 5, 11, tz="Europe/Warsaw"),
    catchup=False,
    tags=["etl", "orders"],
)
def orders_etl():
    """
    Codzienny pipeline ETL: CSV → walidacja → staging → tabele core.

    Zadania:
        extract        — wczytuje orders.csv, zapisuje surowe dane jako parquet
        validate_orders — waliduje rekordy, odkłada kwarantannę do Excela
        load           — ładuje zwalidowane zamówienia + produkty/klientów do bazy
    """

    @task()
    def extract() -> str:
        """Wczytuje orders.csv i zapisuje DataFrame do pliku parquet."""
        from src.extract import load_csv
        from src.load import load_config

        ctx = get_current_context()
        config = load_config()
        raw_data_path = PROJECT_ROOT / config["paths"]["raw_data"]
        df = load_csv(raw_data_path / config["files"]["orders"])

        # /tmp jest zawsze zapisywalny niezależnie od UID kontenera
        tmp_dir = Path("/tmp/orders_etl") / ctx["ds"]
        tmp_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(tmp_dir / "raw_orders.parquet")
        df.to_parquet(out_path, index=False)
        return out_path

    @task()
    def validate_orders(raw_parquet_path: str) -> str:
        """Waliduje zamówienia; kwarantannę i duplikaty zapisuje do Excela."""
        import pandas as pd

        from src.load import load_config, save_quarantine
        from src.validate import validate

        config = load_config()
        df = pd.read_parquet(raw_parquet_path)
        valid, quarantine, duplicates = validate(df)
        save_quarantine(quarantine, "quarantine", config)
        save_quarantine(duplicates, "duplicates", config)

        out_path = str(Path(raw_parquet_path).parent / "valid_orders.parquet")
        valid.to_parquet(out_path, index=False)
        return out_path

    @task()
    def load(valid_parquet_path: str) -> None:
        """Ładuje dane do bazy: staging → core (transakcja atomowa)."""
        import pandas as pd

        from src.connection import get_db_config, get_engine
        from src.copy_io import copy_from_df, copy_from_file
        from src.load import (
            insert_from_staging_to_core,
            insert_raw_file,
            load_config,
            truncate_staging,
        )

        config = load_config()
        engine = get_engine(get_db_config(config))

        raw_data_path = PROJECT_ROOT / config["paths"]["raw_data"]
        products_path = raw_data_path / config["files"]["products"]
        customers_path = raw_data_path / config["files"]["customers"]
        valid_orders = pd.read_parquet(valid_parquet_path)

        with engine.begin() as conn:
            truncate_staging(conn)
            copy_from_file(conn, products_path, table="stag_products")
            copy_from_file(conn, customers_path, table="stag_customers")
            copy_from_df(conn, valid_orders, table="stag_orders")
            insert_from_staging_to_core(conn)
            insert_raw_file(conn, products_path)

    raw_path = extract()
    valid_path = validate_orders(raw_path)
    load(valid_path)


orders_etl_dag = orders_etl()
