import logging
import pandas as pd
import chardet

logger = logging.getLogger(__name__)


def load_csv(path: str) -> pd.DataFrame:
    """Wczytuje CSV jako raw strings z auto-detekcją encodingu i separatora."""
    with open(path, "rb") as f:
        detected = chardet.detect(f.read(10_000))
    encoding = detected["encoding"] or "utf-8"

    with open(path, "r", encoding=encoding, errors="replace") as f:
        first_line = f.readline()
    sep = max([",", ";", "\t", "|"], key=first_line.count)

    df = pd.read_csv(
        path,
        header=0,
        sep=sep,
        encoding=encoding,
        encoding_errors="replace",
        dtype=str,
        keep_default_na=False,
        skipinitialspace=True,
        on_bad_lines="warn",
    )

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    logger.info(
        "csv_loaded",
        extra={"path": str(path), "rows": len(df), "encoding": encoding, "sep": sep},
    )
    return df
