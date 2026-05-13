import hashlib
import logging
from datetime import datetime
from pathlib import Path

import chardet
import yaml
from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def _compute_hash(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def _detect_encoding(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        detected = chardet.detect(f.read(10_000))
    return detected["encoding"] or "utf-8"


def save_quarantine(df, name: str, config: dict) -> None:
    base_dir = Path(__file__).resolve().parents[1]
    today_str = datetime.today().strftime("%Y%m%d_%H_%M_%S")
    output_dir = base_dir / config["paths"]["quarantine"]
    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{config['output']['report_name']}_{name}_{today_str}.xlsx"
    df.to_excel(output_dir / file_name, index=False)


def insert_raw_file(conn: Connection, path: Path | str) -> None:
    file_path = Path(path)
    file_hash = _compute_hash(file_path)
    encoding = _detect_encoding(file_path)
    content = file_path.read_text(encoding=encoding, errors="replace")
    conn.execute(
        text("""
            INSERT INTO raw_products_files (file_name, file_hash, file_content, ingested_at)
            VALUES (:file_name, :file_hash, :file_content, NOW())
            ON CONFLICT (file_hash) DO NOTHING
        """),
        {"file_name": file_path.name, "file_hash": file_hash, "file_content": content},
    )


def truncate_staging(conn: Connection) -> None:
    conn.execute(text("TRUNCATE stag_customers, stag_products, stag_orders"))


def insert_from_staging_to_core(conn: Connection) -> None:
    conn.execute(text("""
        INSERT INTO customers (customer_id, customer_name, email, city, created_at)
        SELECT customer_id, customer_name, email, city, created_at
        FROM stag_customers
        ORDER BY customer_id
        ON CONFLICT DO NOTHING
    """))
    conn.execute(text("""
        INSERT INTO products (product_id, product_name, category, price)
        SELECT product_id, product_name, category, price
        FROM stag_products
        ORDER BY product_id
        ON CONFLICT DO NOTHING
    """))
    conn.execute(text("""
        INSERT INTO rejected_orders (
            order_id, customer_id, product_id, quantity, amount,
            order_date, stag_order_status, order_date_raw, error_reason
        )
        SELECT
            s.order_id, s.customer_id, s.product_id, s.quantity, s.amount,
            s.order_date, s.stag_order_status, s.order_date_raw,
            CASE
                WHEN NOT EXISTS (
                    SELECT 1 FROM products p WHERE p.product_id = s.product_id
                ) THEN 'PRODUCT_NOT_FOUND'
                WHEN NOT EXISTS (
                    SELECT 1 FROM customers c WHERE c.customer_id = s.customer_id
                ) THEN 'CUSTOMER_NOT_FOUND'
                ELSE 'UNKNOWN'
            END
        FROM stag_orders s
        WHERE NOT EXISTS (
                SELECT 1 FROM products p WHERE p.product_id = s.product_id
              )
           OR NOT EXISTS (
                SELECT 1 FROM customers c WHERE c.customer_id = s.customer_id
              )
        ON CONFLICT (order_id) DO NOTHING
    """))
    conn.execute(text("""
        INSERT INTO orders (
            order_id, customer_id, product_id, quantity, amount,
            order_date, order_status
        )
        SELECT
            s.order_id, s.customer_id, s.product_id, s.quantity, s.amount,
            s.order_date, s.stag_order_status
        FROM stag_orders s
        WHERE EXISTS (
                SELECT 1 FROM products p WHERE p.product_id = s.product_id
              )
          AND EXISTS (
                SELECT 1 FROM customers c WHERE c.customer_id = s.customer_id
              )
        ON CONFLICT (order_id) DO NOTHING
    """))
