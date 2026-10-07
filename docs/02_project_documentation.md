# Project Documentation: Courier Delivery Performance & MIS Dashboard

**Author:** Abhishek Kumar | **Role in project:** end to end (data preparation, analysis, SQL, dashboard, documentation)
**Period covered by data:** 1 Jan 2024 - 31 Dec 2025 | **Currency:** INR

## 1. Objective
Measure how well a courier network keeps its delivery promise (SLA), identify weak branches, lanes and periods, explain late deliveries and returns, and present the results in an MIS-style Excel dashboard and an interactive Power BI report.

## 2. Dataset
| Item | Detail |
|---|---|
| Source | Simulated courier data from `01_generate_raw_dataset.py` (seeded, reproducible); not based on any real company |
| Size | 8,080 raw rows (8,000 shipments + 80 duplicates), 16 columns |
| Scope | 15 branches in 5 zones, 3 service types, B2C and B2B customers, 24 months |
| Why simulated | Real courier data is confidential; a generated dataset allowed realistic delivery rules and seeded data-quality problems to practise cleaning |

## 3. Approach and tool roles
| Stage | Tool | Purpose |
|---|---|---|
| 1 | Excel | Cleaning with formulas, lookup tables (City_Map, Branch_Master, Service_SLA), COUNTIFS/SUMIFS/AVERAGEIFS summaries, KPI tiles and 4 charts |
| 2 | Python (Pandas) | Repeatable cleaning with assertions, reconciliation with Excel, `groupby()` EDA, 6 charts |
| 3 | SQL | Relational model, 2 views, 23 queries incl. window functions |
| 4 | Power BI | Four-page dashboard with DAX measures and slicers |

Cross-tool validation: all 10 KPIs checked match between Excel and Python; SQL results match Pandas for KPIs, services, branches and delay reasons (`05_run_sql_queries.py` fails if they differ).

## 4. Data quality issues and treatment
| Issue | Treatment | Reason |
|---|---|---|
| 80 duplicate AWB numbers (70 identical, 10 differing in spelling/spacing) | Drop on `AWB Number`, keep first | AWB is the unique key; comparing whole rows would miss 10 duplicates |
| Status in 10 spellings | Pattern match on "deliver", "rto"/"return", otherwise In Transit | One status must be one group in every report |
| 31 city spellings | `TRIM` + mapping (Bangalore -> Bengaluru, Bombay -> Mumbai, Calcutta -> Kolkata, New Delhi -> Delhi, Madras -> Chennai) + title case | A branch must not split into several |
| Two date formats | Parse each format into a real date | Needed to calculate transit days and monthly trends |
| 40 missing Destination State | Look up from destination city | The city determines the state |
| 50 missing Payment Mode | `Unknown` | Cannot be inferred; deleting rows would change totals |
| 25 weights in grams | Divide by 1000 when above 100 kg | A single parcel above 100 kg is not realistic in this business (assumption) |

## 5. Database design
```
branches       (branch_id PK, branch_name, city, state, zone)
service_levels (service_type PK, sla_days)
shipments      (awb_number PK, booking_date, delivery_date, booking_year/quarter/month/month_no,
                origin_branch_id FK, dest_branch_id FK, service_type FK, weight_kg, freight_amount,
                payment_mode, cod_amount, status, delivery_attempts, delay_return_reason,
                customer_type, customer_rating, transit_days)
```
- `shipments` links to `branches` twice (origin and destination), so queries join `branches` twice with aliases.
- `v_shipment_sla` adds `sla_days`, `sla_status` (On Time / Late / N/A) and `delay_days`; `v_shipment_full` adds origin and destination branch details. Power BI imports `v_shipment_full`.
- `delivery_date`, `transit_days` and `customer_rating` can be NULL (not delivered / not rated). `AVG()` ignores NULLs, which is why average transit days covers delivered shipments only.

## 6. Results
**Overall:** 8,000 shipments (7,426 delivered, 531 RTO, 43 in transit); on-time 82.1% (6,099 of 7,426); average transit 3.53 days; average delay of late shipments 1.85 days; RTO 6.7%; first-attempt delivery 85.1%; freight revenue INR 12.5 lakh; average rating 3.88.

**Service type**
| Service | SLA | On-time % | Avg transit days |
|---|---|---|---|
| Express | 2 | 75.8% | 2.26 |
| Standard | 4 | 83.5% | 3.31 |
| Economy | 7 | 85.6% | 5.18 |

**Branches (destination):** best Meerut 88.9%, Chandigarh 88.4%, Pune 87.2%; weakest Patna 74.8%, Kolkata 75.1%, Delhi 77.9%, Bhopal 79.3%, Mumbai 79.4%. Seven of 15 branches are below the company average.

**Lanes:** North to East is the weakest zone lane (73.1%, 4.03 days), followed by West to East (76.0%) and South to East (76.4%). East-bound Express shipments are late 33.3% of the time. Same-zone and same-city lanes perform best (about 84-85%).

**Time**
- Volume peaks in October (985 shipments over two years, +47% versus September each year) and November.
- On-time % is lowest in October (74.6%) and November (75.1%); also weak in August (77.1%) and July (80.4%).
- Lowest single months: Oct 2024 (73.5%), Nov 2024 (74.3%), Oct 2025 (75.6%).
- 2025 volume is 8% higher than 2024 (4,155 vs 3,845) with unchanged on-time % (82.1% vs 82.2%).

**Why shipments are late (late deliveries only):** hub congestion 33.1%, weather 29.3%, address issue 14.2%, customer unavailable 14.2%, vehicle breakdown 9.3%. Hub congestion is the top cause at 10 of 15 branches; weather is the top cause at the other 5 (Noida, Patna, Pune, Jaipur and Chandigarh).

**Returns (RTO):** COD 11.1%, prepaid 4.5%, credit account 4.4%. RTO reasons: address issue 195, customer refused 171 (69% COD), customer unavailable 165.

**Customers:** late deliveries receive an average rating of 2.73 versus 4.27 for on-time deliveries. Parcel weight has almost no effect on punctuality (81.7% to 82.5% in the three main bands). B2B Express shipments earn the highest average freight (INR 315).

## 7. Recommendations
1. **Seasonal capacity:** add vehicles, staff and sorting hours at Delhi, Mumbai, Kolkata and Patna before October; message customers about expected delays.
2. **Express promise:** add a buffer or restrict the 2-day promise on East-bound lanes until performance improves.
3. **COD controls:** confirmation call/OTP before dispatch and address validation at booking, since COD returns are 2.5 times higher.
4. **Branch scorecard:** report on-time %, RTO % and first-attempt % per branch every month against a 90% target.
5. **Customer care:** proactive updates for shipments past SLA to protect ratings.

## 8. Dashboard
| Page | Content |
|---|---|
| Excel_Dashboard | 6 KPI tiles and 4 charts (on-time % by branch, monthly on-time %, delay reasons, on-time % by service) linked to the Analysis sheet |
| Power BI 1: Executive Overview | KPI cards, monthly shipments vs on-time %, service performance with target line, status donut, slicers |
| Power BI 2: Branch & Lane Performance | Branch bar with conditional colours, zone-to-zone heat map, branch scorecard |
| Power BI 3: Delays, Returns & Customers | Delay reasons, RTO by payment mode, seasonality, rating vs SLA, weight band |
| Power BI 4: Key Insights | Written findings and recommendations |

DAX: Total Shipments, Delivered, RTO Shipments, On-Time %, SLA Breach %, Gap to Target, On-Time Color (for conditional formatting), Avg Transit Days, Avg Delay Days (Late), RTO %, First-Attempt %, Freight Revenue, Shipments LY / YoY %, Late Share %; `DimDate` calendar table; one calculated column (`Weight Band`).

## 9. Limitations and next steps
- Simulated data, so patterns reflect how it was generated. SLA days and the 90% target are assumptions.
- No distance, vehicle, route or complaint data; the analysis relies on recorded reasons.
- In Transit shipments (43) are excluded from on-time and RTO rates.
- Possible extensions: Power Query transformations, a branch scorecard with ranking in Power BI, Excel macros for monthly report refresh.

## 10. Reproducibility
Run scripts 01-05 in order (see README). Each script prints validation checks; `03_python_clean_and_eda.py` fails if Python and Excel KPIs differ and `05_run_sql_queries.py` fails if SQL and Pandas results differ.
