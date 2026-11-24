"""Step 1 - Data cleaning with Pandas and NumPy."""
import re

import numpy as np
import pandas as pd

TEXT_COLS = ["order_id", "customer_name", "segment", "region", "state",
             "category", "sub_category", "product_name"]
TITLE_COLS = ["customer_name", "segment", "region", "state", "category", "sub_category"]
REQUIRED_COLS = ["order_id", "order_date", "customer_name", "product_name", "sales"]


def to_snake(name: str) -> str:
    """'Sub-Category' -> 'sub_category'"""
    return re.sub(r"[^0-9a-zA-Z]+", "_", name.strip()).strip("_").lower()


def parse_dates(series: pd.Series) -> pd.Series:
    """Parse a column that mixes date formats (YYYY-MM-DD, DD/MM/YYYY, DD-Mon-YYYY).

    ISO dates are parsed first on their own, because dayfirst=True would wrongly
    swap the month and day of an ISO date like 2025-03-05.
    """
    text = series.astype("string").str.strip()
    parsed = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
    rest = parsed.isna() & text.notna()
    parsed[rest] = pd.to_datetime(text[rest], format="mixed", dayfirst=True, errors="coerce")
    return parsed


def clean_data(raw: pd.DataFrame):
    """Clean the raw sales data. Returns (clean_dataframe, log_dictionary)."""
    log = {"rows_raw": len(raw)}
    df = raw.copy()
    df.columns = [to_snake(c) for c in df.columns]

    # 1. Text: trim spaces, collapse repeated spaces, fix capitalisation
    for col in TEXT_COLS:
        df[col] = (df[col].astype("string").str.strip()
                   .str.replace(r"\s+", " ", regex=True).replace("", pd.NA))
    for col in TITLE_COLS:
        df[col] = df[col].str.title()

    # 2. Numbers: remove '$' and ',' then convert
    df["sales"] = pd.to_numeric(
        df["sales"].astype("string").str.replace(r"[$,\s]", "", regex=True),
        errors="coerce")
    for col in ["quantity", "discount", "profit"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 3. Dates: several formats mixed in one column
    for col in ["order_date", "ship_date"]:
        df[col] = parse_dates(df[col])

    # 4. Drop rows missing fields we cannot recover
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLS)
    log["rows_dropped_missing_required"] = before - len(df)

    # 5. Remove duplicate rows
    before = len(df)
    df = df.drop_duplicates()
    log["duplicates_removed"] = before - len(df)

    # 6. Fill remaining blanks
    # region -> the region most often seen for the same customer
    known = df.dropna(subset=["region"])
    mode_region = known.groupby("customer_name")["region"].agg(lambda s: s.mode().iat[0])
    log["region_filled"] = int(df["region"].isna().sum())
    df["region"] = df["region"].fillna(df["customer_name"].map(mode_region)).fillna("Unknown")

    # quantity -> median quantity, discount -> 0
    log["quantity_filled"] = int(df["quantity"].isna().sum())
    df["quantity"] = df["quantity"].fillna(df["quantity"].median()).round().astype(int)
    log["discount_filled"] = int(df["discount"].isna().sum())
    df["discount"] = df["discount"].fillna(0).clip(0, 1)

    # profit -> sales x median profit margin of the same sub-category
    valid = df["profit"].notna() & (df["sales"] > 0)
    margin = ((df.loc[valid, "profit"] / df.loc[valid, "sales"])
              .groupby(df.loc[valid, "sub_category"]).median())
    fallback = margin.median() if len(margin) else 0.0
    estimate = df["sales"] * df["sub_category"].map(margin).fillna(fallback)
    log["profit_estimated"] = int(df["profit"].isna().sum())
    df["profit"] = df["profit"].fillna(estimate)

    # 7. New columns
    df["sales"] = df["sales"].round(2)
    df["profit"] = df["profit"].round(2)
    df["profit_margin"] = np.where(df["sales"] > 0, df["profit"] / df["sales"], 0.0).round(4)
    df["order_month"] = df["order_date"].dt.strftime("%Y-%m")
    df["order_year"] = df["order_date"].dt.year
    df["shipping_days"] = (df["ship_date"] - df["order_date"]).dt.days

    # plain Python/NumPy types so the data loads cleanly into SQLite
    df[TEXT_COLS] = df[TEXT_COLS].astype(object)
    df = df.sort_values(["order_date", "order_id"]).reset_index(drop=True)
    log["rows_clean"] = len(df)
    return df, log
