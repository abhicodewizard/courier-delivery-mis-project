# Courier Delivery Performance & MIS Dashboard

An end-to-end data analytics project that takes messy courier shipment data through **Excel → Python (Pandas) → SQL → Power BI** to measure delivery performance against SLA, find weak branches and lanes, and explain delays and returns (RTO).

> **Dataset note:** The data is simulated (8,000 shipments, 15 branches, Jan 2024 - Dec 2025). It was generated with `scripts/01_generate_raw_dataset.py`, is not based on any real company's records, and was deliberately seeded with real-world data quality problems. The findings demonstrate the analytical method, not the results of a real courier company.

## Business problem
A courier company promises delivery within a fixed number of days (Express 2, Standard 4, Economy 7). Operations managers want to know:
1. How often do we keep the promise (on-time %), and how long does delivery take?
2. Which branches, lanes, services and months perform worst?
3. Why are shipments late or returned, and what does it cost in customer satisfaction?

## Workflow
```
Raw CSV (8,080 rows, messy)
   -> Excel    : cleaning formulas, SUMIFS/COUNTIFS summaries, MIS dashboard with charts
   -> Python   : repeatable cleaning + validation + EDA with Pandas, charts
   -> SQL      : 3-table database, 2 views, 23 queries (JOINs, CTEs, window functions)
   -> Power BI : interactive dashboard with DAX measures
   -> Insights and recommendations
```

## Tools
| Tool | Used for |
|---|---|
| Excel | Cleaning (TRIM, PROPER, INDEX/MATCH, date conversion), lookups, COUNTIFS/AVERAGEIFS summaries, dashboard with KPI tiles and charts |
| Python (Pandas, Matplotlib) | Cleaning pipeline, validation checks, reconciliation with Excel, `groupby()` analysis, charts |
| SQL (SQLite; MySQL-compatible) | Schema design, JOINs, GROUP BY/HAVING, CASE WHEN, subqueries, CTEs, views, `RANK`, `LAG`, `ROW_NUMBER`, running totals |
| Power BI | Data model, DAX measures, KPI cards, charts, slicers |

## Data cleaning summary
| Problem in raw data | Fix |
|---|---|
| 80 duplicate AWB numbers (8,080 rows -> 8,000) | Removed on the key `AWB Number` |
| 10 spellings of Status (`delivered`, `DELIVERED `, `Returned`, `rto`...) | Standardised to Delivered / RTO / In Transit |
| 31 city spellings (Bangalore/Bengaluru, Bombay/Mumbai, extra spaces) | `TRIM` + mapping table -> 15 branch cities |
| Two date formats stored as text (120 dates in DD-MM-YYYY) | Parsed into real dates |
| 40 missing Destination State | Recovered from the destination city using the branch master |
| 50 missing Payment Mode | Labelled `Unknown` (cannot be inferred) |
| Service Type and Payment Mode typed in different cases/spaces | `TRIM` + standardised |
| 25 weights entered in grams instead of kg | Values above 100 divided by 1000 |

KPIs were reconciled across Excel, Python and SQL (8,000 shipments, 82.13% on-time, 3.53 average transit days).

## Key findings
- **On-time delivery is 82.1%** (SLA breach 17.9%); average transit time 3.53 days; RTO rate 6.7%; first-attempt delivery 85.1%.
- **Express is the weakest service:** 75.8% on time, versus 83.5% for Standard and 85.6% for Economy.
- **Branch gap:** Patna (74.8%), Kolkata (75.1%) and Delhi (77.9%) are the weakest destinations; Meerut (88.9%) and Chandigarh (88.4%) the strongest. Seven of 15 branches are below the company average.
- **Weakest lane:** North to East (73.1% on time).
- **Peak season:** October-November on-time falls to about 75% while October volume jumps about 47% month over month. The monsoon month of August is also weak (77.1%).
- **Causes of lateness:** hub congestion (33%) and weather (29%) explain 62% of late deliveries.
- **Cash on Delivery risk:** COD shipments are returned 11.1% of the time versus 4.5% for prepaid, about 2.5 times higher.
- **Customer impact:** late deliveries lower the average rating from 4.27 to 2.73.

## Recommendations
1. Add festive-season capacity at the congested hubs (Delhi, Mumbai, Kolkata, Patna) before October.
2. Review the 2-day Express promise on East lanes or add a buffer day.
3. Verify COD orders (call or OTP) and validate addresses at booking to reduce returns.
4. Track a monthly branch scorecard against a 90% on-time target.

## Dashboard
Built in Power BI with four pages: Executive Overview, Branch & Lane Performance, Delays/Returns/Customers, and Key Insights. DAX measures are in [`powerbi/measures.dax`](powerbi/measures.dax) and the theme in `powerbi/theme.json`. An Excel version of the dashboard is in `data/cleaned/courier_excel_analysis.xlsx` (sheet `Excel_Dashboard`).

<!-- After building the dashboard, save screenshots in powerbi/ and uncomment:
![Page 1](powerbi/dashboard_page1.png)
![Page 2](powerbi/dashboard_page2.png)
![Page 3](powerbi/dashboard_page3.png)
-->

## Project structure
```
courier-delivery-mis-project/
├── data/
│   ├── raw/           shipments_raw.csv / .xlsx (messy input), branch_master.csv
│   └── cleaned/       courier_excel_analysis.xlsx, courier_shipments_clean.csv,
│                      powerbi_delivery_data.csv, sql_load/ (branches, service_levels, shipments)
├── scripts/           01 generate data | 02 build Excel | 03 Python clean + EDA | 04 build DB | 05 run SQL
├── sql/               01_schema.sql, 02_views.sql, 03_business_queries.sql
├── database/          courier_mis.db (SQLite)
├── outputs/           python_eda/ (tables), charts/ (PNG), sql_results/ (query outputs)
├── powerbi/           measures.dax, theme.json, dashboard .pbix, screenshots
└── docs/              business problem + data dictionary, project documentation
```

## How to reproduce
```bash
pip install -r requirements.txt
cd scripts
python 01_generate_raw_dataset.py     # creates the raw data
python 02_build_excel_workbook.py     # Excel workbook with formulas (recalculate it in Excel/LibreOffice)
python 03_python_clean_and_eda.py     # clean data + EDA + charts + reconciliation with Excel
python 04_build_database.py           # SQLite database + Power BI file
python 05_run_sql_queries.py          # runs all 23 queries and validates against Pandas
```
**MySQL option:** run `sql/01_schema.sql`, import `data/cleaned/sql_load/branches.csv`, `service_levels.csv`, `shipments.csv` (in that order), then run `sql/02_views.sql` and the queries. The queries were written to be portable but were tested on SQLite.

## SQL concepts demonstrated
Aggregate functions, `GROUP BY`, `HAVING` vs `WHERE`, `INNER JOIN` vs `LEFT JOIN`, joining one table twice (origin and destination branch), `CASE WHEN` and conditional aggregation, subqueries, CTEs, views, `RANK()`, `LAG()`, `ROW_NUMBER()`, running totals with `SUM() OVER`, handling `NULL`.

## Limitations
- Simulated data: the patterns (for example the festive-season dip and the COD return rate) reflect how the data was generated.
- SLA days and the 90% on-time target are assumptions, not company policy.
- No cost, vehicle, route-distance or customer-complaint data, so the analysis cannot explain root causes beyond the recorded reasons.
