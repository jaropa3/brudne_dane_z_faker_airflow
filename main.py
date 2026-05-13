from pathlib import Path

from dotenv import load_dotenv
#przerobić to po apache airflow
from src.connection import get_db_config, get_engine
from src.copy_io import copy_from_df, copy_from_file
from src.extract import load_csv
from src.load import (
    insert_from_staging_to_core,
    insert_raw_file,
    load_config,
    save_quarantine,
    truncate_staging,
)
from src.logger_app import setup_logger
from src.step import step
from src.validate import validate


@step("setup")
def setup_phase():
    load_dotenv(Path(".env"))
    config = load_config()
    db_config = get_db_config(config)
    engine = get_engine(db_config)
    raw_data_path = Path(config["paths"]["raw_data"])
    return engine, raw_data_path, config


@step("extract")
def extract_phase(raw_data_path, config):
    return load_csv(raw_data_path / config["files"]["orders"])


@step("validate")
def validate_phase(orders_df, config):
    valid, quarantine, duplicates = validate(orders_df)
    save_quarantine(quarantine, "quarantine", config)
    save_quarantine(duplicates, "duplicates", config)
    return valid


@step("load")
def load_phase(engine, raw_data_path, valid_orders, config):
    products_path = raw_data_path / config["files"]["products"]
    customers_path = raw_data_path / config["files"]["customers"]
    with engine.begin() as conn:
        truncate_staging(conn)
        copy_from_file(conn, products_path, table="stag_products")
        copy_from_file(conn, customers_path, table="stag_customers")
        copy_from_df(conn, valid_orders, table="stag_orders")
        insert_from_staging_to_core(conn)
        insert_raw_file(conn, products_path)


def main():
    setup_logger("src")
    engine, raw_data_path, config = setup_phase()
    orders_df = extract_phase(raw_data_path, config)
    valid_orders = validate_phase(orders_df, config)
    load_phase(engine, raw_data_path, valid_orders, config)


if __name__ == "__main__":
    main()
