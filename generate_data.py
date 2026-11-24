"""Generate a realistic, deliberately MESSY Superstore-style sales dataset.

The data has the kinds of problems real data has: mixed date formats, '$' signs
inside numbers, inconsistent upper/lower case, extra spaces, blank cells and
duplicate rows. The cleaning step (clean.py) fixes all of them.

Tip: you can replace data/sales_raw.csv with the real Superstore dataset from
Kaggle (see README) and the pipeline will work the same way.
"""
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

CATALOG = {
    "Furniture": {
        "Chairs": [("Ergo Office Chair", 189.0), ("Mesh Task Chair", 129.0),
                   ("Executive Leather Chair", 349.0), ("Stackable Chair", 59.0)],
        "Tables": [("Standing Desk", 399.0), ("Conference Table", 549.0),
                   ("Folding Table", 89.0), ("Coffee Table", 149.0)],
        "Bookcases": [("Oak Bookcase", 219.0), ("Metal Shelf Unit", 119.0),
                      ("Corner Bookcase", 169.0), ("Mini Bookcase", 79.0)],
    },
    "Office Supplies": {
        "Paper": [("A4 Copy Paper Ream", 6.5), ("Recycled Paper Pack", 9.0),
                  ("Photo Paper Pack", 14.0), ("Sticky Notes Bundle", 4.5)],
        "Binders": [("Ring Binder 2in", 5.0), ("Heavy Duty Binder", 8.5),
                    ("Binder Dividers", 3.5), ("Presentation Binder", 11.0)],
        "Storage": [("File Cabinet", 159.0), ("Storage Box Set", 24.0),
                    ("Desk Organizer", 19.0), ("Archive Boxes", 32.0)],
    },
    "Technology": {
        "Phones": [("Smartphone X10", 599.0), ("Budget Phone A2", 199.0),
                   ("Desk Phone Pro", 89.0), ("Rugged Phone R5", 349.0)],
        "Accessories": [("Wireless Mouse", 25.0), ("Mechanical Keyboard", 79.0),
                        ("USB-C Hub", 39.0), ("Laptop Stand", 45.0)],
        "Printers": [("Laser Printer L200", 289.0), ("Inkjet Printer I50", 129.0),
                     ("Label Printer", 99.0), ("Photo Printer P8", 179.0)],
    },
}

BASE_MARGIN = {
    "Chairs": 0.12, "Tables": -0.04, "Bookcases": 0.08,
    "Paper": 0.38, "Binders": 0.30, "Storage": 0.15,
    "Phones": 0.18, "Accessories": 0.26, "Printers": 0.06,
}

REGION_STATES = {
    "East": ["New York", "Pennsylvania", "Ohio"],
    "West": ["California", "Washington", "Oregon"],
    "Central": ["Texas", "Illinois", "Michigan"],
    "South": ["Florida", "Georgia", "Virginia"],
}
SEGMENTS = ["Consumer", "Corporate", "Home Office"]
FIRST = ["Aarav", "Maya", "Liam", "Sofia", "Noah", "Isha", "Ethan", "Zara", "Lucas", "Anaya",
         "Oliver", "Meera", "James", "Riya", "Henry", "Nina", "Daniel", "Tara", "Samuel", "Leah"]
LAST = ["Shah", "Patel", "Smith", "Khan", "Brown", "Mehta", "Garcia", "Nair", "Miller", "Joshi",
        "Davis", "Iyer", "Wilson", "Rao", "Moore", "Gupta", "Taylor", "Bose", "Clark", "Desai"]
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"]


def _make_customers(rng, n=120):
    names = set()
    while len(names) < n:
        names.add(f"{rng.choice(FIRST)} {rng.choice(LAST)}")
    customers = []
    for name in sorted(names):
        region = rng.choice(list(REGION_STATES))
        customers.append({
            "name": name,
            "segment": rng.choice(SEGMENTS),
            "region": region,
            "state": rng.choice(REGION_STATES[region]),
        })
    return customers


def generate(n_orders=1800, seed=42):
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    customers = _make_customers(rng)
    products = [(cat, sub, name, price)
                for cat, subs in CATALOG.items()
                for sub, items in subs.items()
                for name, price in items]

    start = date(2023, 1, 1)
    rows = []
    for i in range(n_orders):
        order_id = f"US-{2023 + i % 3}-{100000 + i}"
        order_date = start + timedelta(days=rng.randint(0, 1094))
        ship_date = order_date + timedelta(days=rng.randint(2, 7))
        cust = rng.choice(customers)
        for _ in range(rng.randint(1, 4)):
            cat, sub, name, price = rng.choice(products)
            qty = rng.randint(1, 8)
            discount = rng.choice([0, 0, 0, 0, 0.1, 0.2, 0.3, 0.4])
            sales = round(price * qty * (1 - discount), 2)
            margin = BASE_MARGIN[sub] - discount * 0.55 + nrng.normal(0, 0.03)
            rows.append({
                "Order ID": order_id,
                "Order Date": order_date,
                "Ship Date": ship_date,
                "Customer Name": cust["name"],
                "Segment": cust["segment"],
                "Region": cust["region"],
                "State": cust["state"],
                "Category": cat,
                "Sub-Category": sub,
                "Product Name": name,
                "Sales": sales,
                "Quantity": qty,
                "Discount": discount,
                "Profit": round(sales * margin, 2),
            })

    df = pd.DataFrame(rows)

    # ---- make it messy ----
    for col in ["Order Date", "Ship Date"]:
        df[col] = [d.strftime(rng.choice(DATE_FORMATS)) for d in df[col]]

    df["Sales"] = [f"${v:,.2f}" if rng.random() < 0.15 else v for v in df["Sales"]]

    def mess_text(v):
        r = rng.random()
        if r < 0.05:
            return v.upper()
        if r < 0.10:
            return v.lower()
        if r < 0.14:
            return f"  {v} "
        return v

    for col in ["Region", "Segment", "Category", "Sub-Category", "Customer Name"]:
        df[col] = df[col].map(mess_text)

    for col, p in {"Region": 0.03, "Discount": 0.03, "Profit": 0.03,
                   "Sales": 0.01, "Quantity": 0.02, "Ship Date": 0.02}.items():
        df.loc[nrng.random(len(df)) < p, col] = np.nan

    dupes = df.sample(frac=0.03, random_state=seed)
    df = pd.concat([df, dupes]).sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


def main(path="data/sales_raw.csv"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(path, index=False)
    print(f"Generated {len(df):,} messy rows -> {path}")


if __name__ == "__main__":
    main()
