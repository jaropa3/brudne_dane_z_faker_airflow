# Zamówienia z kwotą powyżej średniej
# Ile zamówień per miesiąc? (strftime w SQLite)
# Klienci bez żadnego zamówienia (LEFT JOIN + IS NULL)
# Najdroższy produkt w każdej kategorii (GROUP BY + MAX)
# Klienci którzy kupili więcej niż 3 różne produkty
# Przychód per miasto klienta

# Format wyjścia: Każde zapytanie → wynik w konsoli z nagłówkiem.

import pandas as pd
from src.load import load_config
from src.extract import read_input, load_csv
from src.validate import validate
from sqlalchemy import create_engine, text
from pathlib import Path
from src.logger_app import setup_logger
from src.load import save_qarantine, insert_raw_file, insert_from_stagging_to_core, truncat_stag
from src.copy_io import copy_from_file
from src.connection import get_engine, get_db_config
from dotenv import load_dotenv

config = load_config()
env_path = Path(r".env")
load_dotenv(env_path)

def main():
    
    db_config = get_db_config(config)
    engine = get_engine(db_config)
    
    with engine.begin() as conn:
        df_1 = pd.read_sql(text("""
        SELECT customer_id, COUNT(*) AS order_count
        FROM orders
        GROUP BY customer_id
        """), conn)
        print("Ile zamówień ma każdy klient? (GROUP BY + COUNT")
        print(df_1)
        df_2 = pd.read_sql(text("""
            SELECT c.customer_id, c.customer_name, COALESCE(SUM(o.amount), 0) AS total_spent
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.customer_name
        """), conn)
        print("Jaka jest suma wydatków per klient? (GROUP BY + SUM")
        print(df_2)
        df_3 = pd.read_sql(text("""
        SELECT c.customer_id, c.customer_name, SUM(o.amount) AS total_spent
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.customer_name
        ORDER BY total_spent DESC
        LIMIT 10
        """), conn)
        print("\nTop 10 klientów po wartości zakupów")
        print(df_3)
        df_4 = pd.read_sql(text("""
        select o.customer_id, c.customer_name, MAX(o.order_date) as last_order
        from orders o 
        left join customers c on o.customer_id = c.customer_id
        WHERE o.order_date >= NOW() - INTERVAL '30 days'
        group by o.customer_id, c.customer_name
        """), conn)
        print("Klienci którzy złożyli zamówienie w ostatnich 30 dniach")
        print(df_4)
if __name__ == "__main__":

    main()
