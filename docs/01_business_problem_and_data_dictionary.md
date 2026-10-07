# Business Problem and Data Dictionary

## Business problem
A courier company sells three delivery services with a promised delivery time (SLA): Express (2 days), Standard (4 days) and Economy (7 days). Operations and MIS teams need a regular report that answers:
1. How often is the promise kept (on-time %) and how long does delivery take?
2. Which destination branches, lanes (origin zone to destination zone), services and months perform worst?
3. Why are shipments late or returned to origin (RTO), and how does lateness affect customer ratings?
4. Where should management act (capacity, SLA design, COD policy)?

## Tools and why
| Tool | Why |
|---|---|
| Excel | Quick checks, cleaning formulas, SUMIFS-based MIS tables and a simple dashboard that any manager can open |
| Python (Pandas) | Repeatable cleaning with validation and an audit trail |
| SQL | Reusable queries on related tables, including ranking and month-over-month analysis with window functions |
| Power BI | Interactive dashboard with slicers and DAX KPIs |

## Raw file: `data/raw/shipments_raw.csv`
| Column | Meaning |
|---|---|
| AWB Number | Unique tracking number (duplicates in the raw file are repeated rows) |
| Booking Date | Date the shipment was booked (two text formats in the raw file) |
| Delivery Date | Date delivered; blank for RTO and In Transit |
| Origin City / Destination City | Branch city (spellings are inconsistent) |
| Destination State | State of the destination (some blank) |
| Service Type | Express, Standard or Economy |
| Weight (kg) | Parcel weight (25 values were typed in grams) |
| Freight Amount | Courier charge in INR |
| Payment Mode | Prepaid, COD (cash on delivery) or Credit Account |
| COD Amount | Cash to be collected (0 for non-COD) |
| Status | Delivered, RTO (returned to origin) or In Transit (typed in 10 ways) |
| Delivery Attempts | Number of delivery attempts |
| Delay/Return Reason | Reason for a late delivery or a return; blank when there was no issue |
| Customer Type | B2C (individual) or B2B (business) |
| Customer Rating | 1-5 stars; blank when the customer did not rate |

## Reference file: `data/raw/branch_master.csv`
Branch ID, Branch Name, City, State, Zone (North, West, South, East, Central) for 15 branches. Chandigarh, Patna and Bhopal only receive shipments in this data.

## Deliberate data problems
| Problem | Count | Fix |
|---|---|---|
| Duplicate AWB numbers | 80 | Remove, keep first |
| Status written in 10 ways | 180 rows altered | Map to Delivered / RTO / In Transit |
| City spelling variants | 31 raw spellings | `TRIM` + mapping table -> 15 cities |
| Mixed date formats | 70 booking + 50 delivery dates | Parse both formats |
| Missing Destination State | 40 | Recover from city via branch master |
| Missing Payment Mode | 50 | Label `Unknown` |
| Service/Payment text in different cases | about 95 | `TRIM`, standardise |
| Weight in grams | 25 | Divide by 1000 when above 100 |

## Definitions
| Term | Definition |
|---|---|
| Transit Days | Delivery Date - Booking Date (Delivered shipments only) |
| SLA Days | Express 2, Standard 4, Economy 7 (assumed business rule) |
| On Time / Late | Transit Days <= SLA Days / Transit Days > SLA Days |
| Delay Days | Transit Days - SLA Days for late shipments |
| On-Time % | On-time deliveries / Delivered shipments |
| RTO % | RTO shipments / (Delivered + RTO); In Transit excluded because the outcome is not known yet |
| First-Attempt % | Delivered in 1 attempt / Delivered |
| Data snapshot date | 31 Dec 2025 (shipments not delivered by then are In Transit) |
