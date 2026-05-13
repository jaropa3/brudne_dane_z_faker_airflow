import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)

VALID_STATUSES = {"pending", "paid", "refunded", "cancelled"}

REQUIRED_COLUMNS = [
    "order_id", "customer_id", "product_id",
    "quantity", "amount", "order_date", "status",
]
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%Y%m%d"]


def _parse_date(val) -> datetime | None:
    if pd.isna(val) or not isinstance(val, str):
        return None
    for fmt in DATE_FORMATS:
        try:
            # naive datetime — caller must keep tz consistency
            return datetime.strptime(val.strip(), fmt)
        except ValueError:
            continue
    return None


def _check_required_columns(df: pd.DataFrame) -> None:
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")


def _cast_types(df: pd.DataFrame) -> pd.DataFrame:
    df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce").astype("Int64")
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce").astype("Int64")
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").astype("Int64")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    # extract.py reads CSV with dtype=str + keep_default_na=False, so missing values
    # come through as the literal strings "", "nan", "<NA>" — collapse them to pd.NA.
    df["status"] = (
        df["status"].astype(str).str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "<NA>": pd.NA})
    )
    return df


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    df["order_date_raw"] = df["order_date"]
    df["order_date"] = pd.to_datetime(
        df["order_date_raw"].apply(_parse_date),
        errors="coerce",
    )
    return df


def _split_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values("order_date")
    duplicates = df[df.duplicated(subset=["order_id"], keep="last")]
    df = df.drop_duplicates(subset=["order_id"], keep="last")
    return df, duplicates


def _apply_rules(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    # All timestamps in this module are tz-naive (see _parse_date). Use a naive "now"
    # to avoid TypeError on comparison.
    now = pd.Timestamp(datetime.now(timezone.utc).replace(tzinfo=None))
    rules = {
        "not_null_keys":   df[["order_id", "customer_id", "product_id", "status"]].notna().all(axis=1),
        "valid_date":      df["order_date"].notna(),
        "not_future_date": df["order_date"] <= now,
        "positive_qty":    df["quantity"] > 0,
        "positive_amount": df["amount"] > 0,
        "valid_status":    df["status"].isin(VALID_STATUSES),
    }
    rule_df = pd.DataFrame({f"fail_{name}": ~mask for name, mask in rules.items()})
    # not_future_date is meaningless when the date itself failed to parse.
    rule_df.loc[~rules["valid_date"], "fail_not_future_date"] = False
    final_mask = ~rule_df.any(axis=1)
    return rule_df, final_mask


def validate(df: pd.DataFrame):
    df = df.copy()
    _check_required_columns(df)
    df = _cast_types(df)
    df = _parse_dates(df)
    df, duplicates = _split_duplicates(df)

    rule_df, final_mask = _apply_rules(df)

    valid = df[final_mask].copy()
    quarantine = df[~final_mask].copy().join(rule_df[~final_mask])

    rule_stats = {name: int(col.sum()) for name, col in rule_df.items()}
    logger.info(
        "data_valid_summary",
        extra={
            "total_rows":      len(df),
            "valid_rows":      len(valid),
            "quarantine_rows": len(quarantine),
            "duplicates":      len(duplicates),
            "rules_failed":    rule_stats,
        },
    )

    return valid, quarantine, duplicates
