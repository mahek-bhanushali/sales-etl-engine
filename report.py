"""Step 3 - Run the SQL queries and build a formatted Excel report."""
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")
MONEY_WORDS = ("sales", "profit", "revenue")


def load_queries(sql_path) -> dict:
    """Split queries.sql into {name: sql} using the '-- name:' markers."""
    text = Path(sql_path).read_text(encoding="utf-8")
    parts = re.split(r"^-- name:\s*(\w+)\s*$", text, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def compute_kpis(conn) -> list:
    """Headline numbers. Uses NumPy for the statistics."""
    df = pd.read_sql_query(
        "SELECT order_id, customer_id, sales, profit, order_month FROM sales", conn)
    order_totals = df.groupby("order_id")["sales"].sum().to_numpy()
    month_totals = df.groupby("order_month")["sales"].sum()
    return [
        ("Total sales", float(np.sum(df["sales"])), "money"),
        ("Total profit", float(np.sum(df["profit"])), "money"),
        ("Overall profit margin", float(np.sum(df["profit"]) / np.sum(df["sales"])), "pct"),
        ("Number of orders", int(len(order_totals)), "int"),
        ("Number of customers", int(df["customer_id"].nunique()), "int"),
        ("Average order value", float(np.mean(order_totals)), "money"),
        ("Median order value", float(np.median(order_totals)), "money"),
        ("90th percentile order value", float(np.percentile(order_totals, 90)), "money"),
        ("Best month", f"{month_totals.idxmax()} ({month_totals.max():,.0f})", "text"),
        ("Weakest month", f"{month_totals.idxmin()} ({month_totals.min():,.0f})", "text"),
    ]


def _style_header(ws, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
    ws.freeze_panes = "A2"


def _autofit(ws):
    for col in ws.columns:
        width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(width + 3, 45)


def _write_table(ws, df):
    ws.append(list(df.columns))
    for row in df.itertuples(index=False):
        ws.append(list(row))
    _style_header(ws, len(df.columns))
    for idx, name in enumerate(df.columns, start=1):
        if any(w in name for w in MONEY_WORDS) and "pct" not in name:
            for r in range(2, len(df) + 2):
                ws.cell(row=r, column=idx).number_format = "#,##0.00"
    _autofit(ws)


def _add_chart(ws, df, kind, title, y_cols):
    chart = LineChart() if kind == "line" else BarChart()
    chart.title, chart.height, chart.width = title, 8.5, 18
    for col_idx in y_cols:
        data = Reference(ws, min_col=col_idx, min_row=1, max_row=len(df) + 1)
        chart.add_data(data, titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=len(df) + 1))
    ws.add_chart(chart, f"{get_column_letter(len(df.columns) + 2)}2")


def build_report(db_path, sql_path, out_path, log=None) -> Path:
    queries = load_queries(sql_path)
    wb = Workbook()

    with sqlite3.connect(db_path) as conn:
        # --- Summary sheet ---
        ws = wb.active
        ws.title = "Summary"
        ws["A1"] = "Sales Report - Key Numbers"
        ws["A1"].font = Font(bold=True, size=15)
        ws.append([])
        ws.append(["Metric", "Value"])
        for cell in ws[3]:
            cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        for label, value, kind in compute_kpis(conn):
            ws.append([label, value])
            cell = ws.cell(row=ws.max_row, column=2)
            cell.alignment = Alignment(horizontal="right")
            if kind == "money":
                cell.number_format = "#,##0.00"
            elif kind == "pct":
                cell.number_format = "0.00%"
        if log:
            ws.append([])
            ws.append(["Data cleaning log", "Rows"])
            for cell in ws[ws.max_row]:
                cell.fill, cell.font = HEADER_FILL, HEADER_FONT
            for key, val in log.items():
                ws.append([key.replace("_", " ").capitalize(), val])
        ws.column_dimensions["A"].width = 34
        ws.column_dimensions["B"].width = 26

        # --- One sheet per SQL query ---
        for name, sql in queries.items():
            df = pd.read_sql_query(sql, conn)
            sheet = wb.create_sheet(name[:31])
            _write_table(sheet, df)
            if name == "monthly_sales" and not df.empty:
                _add_chart(sheet, df, "line", "Monthly sales and profit", [2, 3])
            elif name == "sales_by_region" and not df.empty:
                _add_chart(sheet, df, "bar", "Sales and profit by region", [2, 3])
            elif name == "yearly_growth" and not df.empty:
                _add_chart(sheet, df, "bar", "Yearly sales", [2])

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path
