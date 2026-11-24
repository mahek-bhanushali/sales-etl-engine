# Sales ETL Engine

An automated **data cleaning -> SQL analysis -> Excel reporting** pipeline built with
**Python, Pandas, NumPy, SQLite and openpyxl**. One command turns a messy sales CSV into a
clean database and a formatted Excel report with charts.

## What it does

1. **Cleans** messy data (Pandas + NumPy): mixed date formats, `$` signs inside numbers, inconsistent
upper/lower case, extra spaces, blank cells and duplicate rows. Adds `profit\_margin`,
`order\_month`, `order\_year` and `shipping\_days`.
2. **Loads** the clean data into SQLite as three related tables: `customers`, `products`, `sales`.
3. **Analyses** the data with 8 SQL queries (JOINs, GROUP BY, HAVING-style filters, CASE and a `LAG` window function).
4. **Reports** the results in `output/sales\_report.xlsx`: a KPI summary (mean, median, 90th percentile with NumPy), one sheet per query, and charts.

## Pipeline

```
data/sales\_raw.csv -> clean.py -> load\_db.py -> queries.sql -> report.py -> output/sales\_report.xlsx
                         \\\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ main.py runs everything \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_/
```

## Project structure

```
salesflow-pipeline/
├── main.py            # runs the full pipeline
├── generate\_data.py   # creates a sample messy dataset
├── clean.py           # data cleaning (Pandas, NumPy)
├── load\_db.py         # SQLite schema + loading
├── queries.sql        # 8 analysis queries
├── report.py          # Excel report (openpyxl)
├── tests/             # pytest tests
├── data/              # raw CSV, clean CSV, SQLite database
└── output/            # generated Excel report
```

## How to run

```bash
git clone https://github.com/mahek-bhanushali/sales-etl-engine.git
cd sales-etl-engine
python -m venv venv
venv\\Scripts\\activate          # Windows  (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python main.py
```

The first run generates a sample messy dataset automatically. Open `output/sales\_report.xlsx` to see the report.

Run the tests: `pytest -v`

## Cleaning rules

|Problem|Fix|
|-|-|
|Dates in 3 different formats|Parsed into one standard date format|
|`$1,200.50` stored as text|Symbols removed, converted to numbers|
|`consumer`, `CONSUMER`, `Consumer`|Trimmed and standardised to `Consumer`|
|Duplicate rows|Removed|
|Missing sales / order date|Row dropped (cannot be recovered)|
|Missing region|Filled with the customer's usual region|
|Missing quantity|Filled with the median quantity|
|Missing discount|Set to 0|
|Missing profit|Estimated from the median profit margin of the same sub-category|

## Using your own data (e.g. Kaggle Superstore)

Put your CSV at `data/sales\_raw.csv` (or run `python main.py --raw path/to/file.csv`).
It needs these columns: `Order ID, Order Date, Ship Date, Customer Name, Segment, Region, State, Category, Sub-Category, Product Name, Sales, Quantity, Discount, Profit`.

## Sample findings (from the generated data)

* Discounts above 20% push profit margin negative, while undiscounted sales earn a margin of about 9%.
* Tables lose money overall, even though they sell well.
* The East region has the lowest profit margin.

## Possible improvements

* Add a dashboard (Streamlit), schedule the pipeline to run daily, or connect to PostgreSQL.

