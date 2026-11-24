-- All analysis queries. Each block starts with "-- name: <sheet_name>".
-- report.py runs every block and writes the result to its own Excel sheet.

-- name: top_10_products
SELECT p.product_name,
       p.category,
       ROUND(SUM(s.sales), 2)  AS total_sales,
       ROUND(SUM(s.profit), 2) AS total_profit,
       SUM(s.quantity)         AS units_sold
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY p.product_id
ORDER BY total_sales DESC
LIMIT 10;

-- name: monthly_sales
SELECT order_month                AS month,
       ROUND(SUM(sales), 2)       AS total_sales,
       ROUND(SUM(profit), 2)      AS total_profit,
       COUNT(DISTINCT order_id)   AS orders
FROM sales
GROUP BY order_month
ORDER BY order_month;

-- name: sales_by_region
SELECT c.region,
       ROUND(SUM(s.sales), 2)  AS total_sales,
       ROUND(SUM(s.profit), 2) AS total_profit,
       ROUND(100.0 * SUM(s.profit) / SUM(s.sales), 2) AS profit_margin_pct,
       COUNT(DISTINCT s.order_id) AS orders
FROM sales s
JOIN customers c ON c.customer_id = s.customer_id
GROUP BY c.region
ORDER BY total_sales DESC;

-- name: sales_by_category
SELECT p.category,
       p.sub_category,
       ROUND(SUM(s.sales), 2)  AS total_sales,
       ROUND(SUM(s.profit), 2) AS total_profit,
       ROUND(100.0 * SUM(s.profit) / SUM(s.sales), 2) AS profit_margin_pct
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY p.category, p.sub_category
ORDER BY p.category, total_sales DESC;

-- name: top_10_customers
SELECT c.customer_name,
       c.segment,
       c.region,
       COUNT(DISTINCT s.order_id) AS orders,
       ROUND(SUM(s.sales), 2)     AS total_sales
FROM sales s
JOIN customers c ON c.customer_id = s.customer_id
GROUP BY c.customer_id
ORDER BY total_sales DESC
LIMIT 10;

-- name: least_profitable_subcats
SELECT p.sub_category,
       p.category,
       ROUND(SUM(s.profit), 2) AS total_profit,
       ROUND(100.0 * SUM(s.profit) / SUM(s.sales), 2) AS profit_margin_pct
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY p.sub_category, p.category
ORDER BY total_profit ASC
LIMIT 5;

-- name: discount_impact
SELECT CASE
           WHEN discount = 0    THEN '1. No discount'
           WHEN discount <= 0.1 THEN '2. Up to 10%'
           WHEN discount <= 0.2 THEN '3. 11-20%'
           ELSE                      '4. Above 20%'
       END                          AS discount_band,
       COUNT(*)                     AS order_lines,
       ROUND(SUM(sales), 2)         AS total_sales,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2) AS profit_margin_pct
FROM sales
GROUP BY discount_band
ORDER BY discount_band;

-- name: yearly_growth
SELECT order_year AS year,
       total_sales,
       ROUND(100.0 * (total_sales - LAG(total_sales) OVER (ORDER BY order_year))
             / LAG(total_sales) OVER (ORDER BY order_year), 2) AS yoy_growth_pct
FROM (
    SELECT order_year, ROUND(SUM(sales), 2) AS total_sales
    FROM sales
    GROUP BY order_year
)
ORDER BY order_year;
