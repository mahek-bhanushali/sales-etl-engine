"""Run the whole pipeline with one command:  python main.py"""
import argparse
import logging
from pathlib import Path

import pandas as pd

from clean import clean_data
from generate_data import main as generate_raw_data
from load_db import load_to_db
from report import build_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("salesflow")


def run(raw_path, db_path, sql_path, report_path):
    if not Path(raw_path).exists():
        log.info("No raw data found - generating a sample messy dataset")
        generate_raw_data(raw_path)

    log.info("STEP 1/4  Reading raw data: %s", raw_path)
    raw = pd.read_csv(raw_path)

    log.info("STEP 2/4  Cleaning data")
    clean, cleaning_log = clean_data(raw)
    for key, value in cleaning_log.items():
        log.info("          %-32s %s", key, value)
    Path("data").mkdir(exist_ok=True)
    clean.to_csv("data/sales_clean.csv", index=False)

    log.info("STEP 3/4  Loading into SQLite: %s", db_path)
    counts = load_to_db(clean, db_path)
    log.info("          tables loaded: %s", counts)

    log.info("STEP 4/4  Running SQL queries and building Excel report")
    out = build_report(db_path, sql_path, report_path, cleaning_log)
    log.info("DONE - report saved to %s", out)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sales data cleaning & reporting pipeline")
    parser.add_argument("--raw", default="data/sales_raw.csv", help="raw CSV file")
    parser.add_argument("--db", default="data/sales.db", help="SQLite database path")
    parser.add_argument("--sql", default="queries.sql", help="SQL queries file")
    parser.add_argument("--out", default="output/sales_report.xlsx", help="Excel report path")
    args = parser.parse_args()
    run(args.raw, args.db, args.sql, args.out)
