-- =============================================================
-- schema.sql — full DDL for the ETL target database.
-- Re-runnable: drops everything first, then recreates.
-- Run on a fresh PostgreSQL database:
--     psql -U <user> -d <dbname> -f sql/schema.sql
-- =============================================================

BEGIN;

-- ---- drop in reverse-dependency order -----------------------
DROP TABLE IF EXISTS rejected_orders     CASCADE;
DROP TABLE IF EXISTS raw_products_files  CASCADE;
DROP TABLE IF EXISTS stag_orders         CASCADE;
DROP TABLE IF EXISTS stag_products       CASCADE;
DROP TABLE IF EXISTS stag_customers      CASCADE;
DROP TABLE IF EXISTS orders              CASCADE;
DROP TABLE IF EXISTS products            CASCADE;
DROP TABLE IF EXISTS customers           CASCADE;

-- =============================================================
-- core tables (parents first because of FKs)
-- =============================================================

CREATE TABLE products (
    product_id   INTEGER       PRIMARY KEY,
    product_name TEXT          NOT NULL,
    category     TEXT          NOT NULL,
    price        NUMERIC(10,2) NOT NULL,
    CONSTRAINT uq_products_name UNIQUE (product_name)
);

CREATE TABLE customers (
    customer_id   INTEGER   PRIMARY KEY,
    customer_name TEXT      NOT NULL,
    email         TEXT      NOT NULL CHECK (position('@' IN email) > 1),
    city          TEXT      NOT NULL,
    created_at    TIMESTAMP NOT NULL,
    CONSTRAINT uq_customers_email UNIQUE (email)
);

CREATE TABLE orders (
    order_id     INTEGER       PRIMARY KEY,
    customer_id  INTEGER       NOT NULL REFERENCES customers(customer_id),
    product_id   INTEGER       NOT NULL REFERENCES products(product_id),
    quantity     INTEGER       NOT NULL CHECK (quantity > 0),
    amount       NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
    order_date   TIMESTAMP     NOT NULL,
    order_status VARCHAR(9)    NOT NULL,
    created_at   TIMESTAMP     NOT NULL DEFAULT now()
);

CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_product_id  ON orders(product_id);
CREATE INDEX idx_orders_order_date  ON orders(order_date);

-- =============================================================
-- staging tables (truncated at the start of each load).
-- Column order MUST match the COPY input — the pipeline relies
-- on positional COPY (HEADER true only skips the header line).
-- =============================================================

CREATE TABLE stag_products (
    product_id   INTEGER,
    product_name TEXT,
    category     TEXT,
    price        NUMERIC
);

CREATE TABLE stag_customers (
    customer_id   INTEGER,
    customer_name TEXT,
    email         TEXT,
    city          TEXT,
    created_at    TIMESTAMP
);

CREATE TABLE stag_orders (
    order_id          INTEGER,
    customer_id       INTEGER,
    product_id        INTEGER,
    quantity          INTEGER,
    amount            NUMERIC,
    order_date        TIMESTAMP,
    stag_order_status TEXT,
    order_date_raw    TEXT          -- raw, unparsed CSV value (audit trail)
);

-- =============================================================
-- audit / rejection tables
-- =============================================================

CREATE TABLE rejected_orders (
    order_id          INTEGER   UNIQUE,
    customer_id       INTEGER,
    product_id        INTEGER,
    quantity          INTEGER,
    amount            NUMERIC,
    order_date        TIMESTAMP,
    stag_order_status TEXT,
    order_date_raw    TEXT,
    error_reason      TEXT,
    rejected_at       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE raw_products_files (
    id           BIGSERIAL PRIMARY KEY,
    file_name    TEXT      NOT NULL,
    file_hash    TEXT      NOT NULL,
    file_content TEXT      NOT NULL,
    ingested_at  TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_raw_products_files_hash UNIQUE (file_hash)
);

COMMIT;
