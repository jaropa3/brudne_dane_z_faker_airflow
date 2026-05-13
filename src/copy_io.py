import io
import logging
from pathlib import Path

import chardet
import pandas as pd
from psycopg2 import sql
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


def _detect_encoding(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        detected = chardet.detect(f.read(10_000))
    return detected["encoding"] or "utf-8"


def _copy_buffer(conn: Connection, buf, table: str) -> None:
    """COPY into table using the DBAPI cursor of the given SQLAlchemy connection.

    Runs inside the caller's transaction — no commit/rollback here.
    """
    raw_cur = conn.connection.cursor()
    try:
        raw_cur.copy_expert(
            sql.SQL("COPY {} FROM STDIN WITH (FORMAT csv, HEADER true)")
                .format(sql.Identifier(table)),
            buf,
        )
    finally:
        raw_cur.close()


def copy_from_file(conn: Connection, file_path: Path | str, table: str) -> None:
    file_path = Path(file_path)
    encoding = _detect_encoding(file_path)
    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        _copy_buffer(conn, f, table)
    logger.info("copy_from_file", extra={"path": str(file_path), "table": table})


def copy_from_df(conn: Connection, df: pd.DataFrame, table: str) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    _copy_buffer(conn, buf, table)
    logger.info("copy_from_df", extra={"rows": len(df), "table": table})
