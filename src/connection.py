from sqlalchemy import create_engine
import os
from sqlalchemy.engine import URL

def get_db_config(config: dict) -> dict:
        
    db = {
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        # POSTGRES_HOST nadpisuje wartość z config.yaml — przydatne w Dockerze,
        # gdzie serwis nazywa się "postgres", a nie "localhost".
        "host": os.getenv("POSTGRES_HOST") or config["database"]["host"],
        "port": config["database"]["port"],
        "dbname": config["database"]["DB_name"],
    }

    missing = [k for k, v in db.items() if not v]
    if missing:
        raise ValueError(f"Missing db config: {missing}")

    return db

def get_engine(db_config: dict):
    
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"],
        database=db_config["dbname"],
    )

    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )