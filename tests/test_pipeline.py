import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clean import clean_data  # noqa: E402
from load_db import load_to_db  # noqa: E402
from report import build_report, load_queries  # noqa: E402

COLUMNS = ["Order ID", "Order Date", "Ship Date", "Customer Name", "Segment", "Region",
           "State", "Category", "Sub-Category", "Product Name", "Sales", "Quantity",
           "Discount", "Profit"]


def make_raw():
    rows = [
        ["A-1", "2025-03-05", "2025-03-08", "Maya Shah", "consumer", "East", "Ohio",
         "Technology", "Phones", "Smartphone X10", "$1,200.50", 2, 0.1, 240.10],
        # exact duplicate of the row above
        ["A-1", "2025-03-05", "2025-03-08", "Maya Shah", "consumer", "East", "Ohio",
         "Technology", "Phones", "Smartphone X10", "$1,200.50", 2, 0.1, 240.10],
        # messy text, other date format, blank region/discount/profit
        ["A-2", "06/03/2025", "09/03/2025", "  maya  shah ", "CONSUMER", None, "Ohio",
         "technology", "phones", "Smartphone X10", 600.0, 1, None, None],
        # missing sales -> must be dropped
        ["A-3", "2025-04-01", "2025-04-04", "Liam Khan", "Corporate", "West", "Oregon",
         "Furniture", "Chairs", "Ergo Office Chair", None, 1, 0, 20.0],
        # unreadable date -> must be dropped
        ["A-4", "not-a-date", "2025-04-04", "Liam Khan", "Corporate", "West", "Oregon",
         "Furniture", "Chairs", "Ergo Office Chair", 189.0, 1, 0, 20.0],
    ]
    return pd.DataFrame(rows, columns=COLUMNS)


def test_cleaning_rules():
    df, log = clean_data(make_raw())
    assert len(df) == 2                                # duplicate + 2 bad rows removed
    assert log["duplicates_removed"] == 1
    assert log["rows_dropped_missing_required"] == 2
    assert df["sales"].tolist() == [1200.5, 600.0]     # '$' and ',' removed
    assert df["order_date"].dt.strftime("%Y-%m-%d").tolist() == ["2025-03-05", "2025-03-06"]
    assert set(df["customer_name"]) == {"Maya Shah"}   # spaces + case fixed
    assert set(df["segment"]) == {"Consumer"}
    assert df["region"].tolist() == ["East", "East"]   # filled from the same customer
    assert df["discount"].tolist() == [0.1, 0.0]
    assert df["profit"].notna().all()                  # missing profit estimated


def test_new_columns():
    df, _ = clean_data(make_raw())
    assert df.loc[0, "order_month"] == "2025-03"
    assert df.loc[0, "shipping_days"] == 3
    assert round(df.loc[0, "profit_margin"], 4) == round(240.10 / 1200.5, 4)


def test_database_and_report(tmp_path):
    df, log = clean_data(make_raw())
    db = tmp_path / "test.db"
    counts = load_to_db(df, db)
    assert counts == {"customers": 1, "products": 1, "sales": 2}

    with sqlite3.connect(db) as conn:
        total = conn.execute("SELECT ROUND(SUM(sales),2) FROM sales").fetchone()[0]
    assert total == 1800.5

    sql_path = Path(__file__).resolve().parent.parent / "queries.sql"
    assert len(load_queries(sql_path)) == 8
    out = build_report(db, sql_path, tmp_path / "report.xlsx", log)
    assert out.exists()
