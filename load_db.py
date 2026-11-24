"""Step 2 - Load the clean data into a SQLite database (3 related tables)."""
import sqlite3
from pathlib import Path

import pandas as pd

SCHEMA = """
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL UNIQUE,
    segment       TEXT,
    region        TEXT,
    state         TEXT
);

CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL UNIQUE,
    category     TEXT,
    sub_category TEXT
);

CREATE TABLE sales (
    sale_id       INTEGER PRIMARY KEY,
    order_id      TEXT NOT NULL,
    order_date    TEXT NOT NULL,
    ship_date     TEXT,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    sales         REAL NOT NULL,
    quantity      INTEGER NOT NULL,
    discount      REAL NOT NULL,
    profit        REAL NOT NULL,
    profit_margin REAL,
    order_month   TEXT,
    order_year    INTEGER,
    shipping_days REAL
);

CREATE INDEX idx_sales_customer ON sales(customer_id);
CREATE INDEX idx_sales_product  ON sales(product_id);
CREATE INDEX idx_sales_month    ON sales(order_month);
"""


def load_to_db(df: pd.DataFrame, db_path) -> dict:
    """Split the flat table into customers / products / sales and store them."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    customers = (df[["customer_name", "segment", "region", "state"]]
                 .drop_duplicates("customer_name").reset_index(drop=True))
    customers.insert(0, "customer_id", customers.index + 1)

    products = (df[["product_name", "category", "sub_category"]]
                .drop_duplicates("product_name").reset_index(drop=True))
    products.insert(0, "product_id", products.index + 1)

    fact = (df.merge(customers[["customer_id", "customer_name"]], on="customer_name")
              .merge(products[["product_id", "product_name"]], on="product_name"))
    fact = fact[["order_id", "order_date", "ship_date", "customer_id", "product_id",
                 "sales", "quantity", "discount", "profit", "profit_margin",
                 "order_month", "order_year", "shipping_days"]].copy()
    for col in ["order_date", "ship_date"]:
        fact[col] = fact[col].dt.strftime("%Y-%m-%d")
    fact = fact.astype(object).where(fact.notna(), None)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        customers.to_sql("customers", conn, if_exists="append", index=False)
        products.to_sql("products", conn, if_exists="append", index=False)
        fact.to_sql("sales", conn, if_exists="append", index=False)

    return {"customers": len(customers), "products": len(products), "sales": len(fact)}
