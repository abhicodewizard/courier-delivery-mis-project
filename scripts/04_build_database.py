"""
Stage 4 - Build the SQL database from the clean CSV.

Run from the scripts/ folder:  python 04_build_database.py

Creates ../database/courier_mis.db (SQLite) using sql/01_schema.sql and sql/02_views.sql.
Also writes:
  ../data/cleaned/sql_load/branches.csv, service_levels.csv, shipments.csv   (for a MySQL import)
  ../data/cleaned/powerbi_delivery_data.csv                                  (for Power BI)
"""
import os
import sqlite3

import pandas as pd

CLEAN = "../data/cleaned/courier_shipments_clean.csv"
BRANCH = "../data/raw/branch_master.csv"
DB = "../database/courier_mis.db"
LOAD_DIR = "../data/cleaned/sql_load"
PBI_CSV = "../data/cleaned/powerbi_delivery_data.csv"
os.makedirs("../database", exist_ok=True)
os.makedirs(LOAD_DIR, exist_ok=True)

# keep the text 'None' (no delay reason) as text; only truly blank cells become NULL
df = pd.read_csv(CLEAN, keep_default_na=False, na_values=[""])
bm = pd.read_csv(BRANCH)

branches = bm.rename(columns={"Branch ID": "branch_id", "Branch Name": "branch_name", "City": "city",
                              "State": "state", "Zone": "zone"})
service_levels = pd.DataFrame({"service_type": ["Express", "Standard", "Economy"], "sla_days": [2, 4, 7]})
city_to_id = dict(zip(bm["City"], bm["Branch ID"]))

ship = pd.DataFrame({
    "awb_number": df["AWB Number"], "booking_date": df["Booking Date"], "delivery_date": df["Delivery Date"],
    "booking_year": df["Booking Year"], "booking_quarter": df["Booking Quarter"],
    "booking_month": df["Booking Month"], "booking_month_no": df["Booking Month No"],
    "origin_branch_id": df["Origin City"].map(city_to_id), "dest_branch_id": df["Destination City"].map(city_to_id),
    "service_type": df["Service Type"], "weight_kg": df["Weight (kg)"], "freight_amount": df["Freight Amount"],
    "payment_mode": df["Payment Mode"], "cod_amount": df["COD Amount"], "status": df["Status"],
    "delivery_attempts": df["Delivery Attempts"], "delay_return_reason": df["Delay/Return Reason"],
    "customer_type": df["Customer Type"], "customer_rating": df["Customer Rating"], "transit_days": df["Transit Days"],
})
assert ship["origin_branch_id"].notna().all() and ship["dest_branch_id"].notna().all()
assert len(ship) == 8000

branches.to_csv(f"{LOAD_DIR}/branches.csv", index=False)
service_levels.to_csv(f"{LOAD_DIR}/service_levels.csv", index=False)
ship.to_csv(f"{LOAD_DIR}/shipments.csv", index=False)

# ---- create database ---------------------------------------------------------
if os.path.exists(DB):
    os.remove(DB)
con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys = ON")          # SQLite enforces foreign keys only when asked
con.executescript(open("../sql/01_schema.sql").read())


def load(table, frame):
    frame = frame.astype(object).where(frame.notna(), None)       # NaN -> NULL
    cols = ",".join(frame.columns)
    marks = ",".join("?" * len(frame.columns))
    con.executemany(f"INSERT INTO {table} ({cols}) VALUES ({marks})", frame.itertuples(index=False, name=None))


load("branches", branches)            # parents first, then the child table
load("service_levels", service_levels)
load("shipments", ship)
con.executescript(open("../sql/02_views.sql").read())
con.commit()

# ---- sanity checks -----------------------------------------------------------
for t in ("branches", "service_levels", "shipments"):
    print(f"{t:15s} rows:", con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
print("foreign key problems:", con.execute("PRAGMA foreign_key_check").fetchall())
n_null_transit = con.execute("SELECT COUNT(*) FROM shipments WHERE transit_days IS NULL").fetchone()[0]
assert n_null_transit == (df["Status"] != "Delivered").sum()
rev = con.execute("SELECT ROUND(SUM(freight_amount),0) FROM shipments").fetchone()[0]
assert abs(rev - df["Freight Amount"].sum()) < 1, "DB revenue does not match clean CSV"
print("Total freight revenue in DB matches the clean CSV:", rev)

# ---- export flat file for Power BI (friendly column names) ---------------------
pbi = pd.read_sql_query("""
    SELECT awb_number AS "AWB Number", booking_date AS "Booking Date", delivery_date AS "Delivery Date",
           booking_year AS "Booking Year", booking_quarter AS "Booking Quarter", booking_month AS "Booking Month",
           booking_month_no AS "Booking Month No",
           origin_city AS "Origin City", origin_state AS "Origin State", origin_zone AS "Origin Zone",
           dest_city AS "Destination City", dest_state AS "Destination State", dest_zone AS "Destination Zone",
           service_type AS "Service Type", sla_days AS "SLA Days", weight_kg AS "Weight (kg)",
           freight_amount AS "Freight Amount", payment_mode AS "Payment Mode", cod_amount AS "COD Amount",
           status AS "Status", delivery_attempts AS "Delivery Attempts", delay_return_reason AS "Delay/Return Reason",
           customer_type AS "Customer Type", customer_rating AS "Customer Rating", transit_days AS "Transit Days",
           sla_status AS "SLA Status", delay_days AS "Delay Days"
    FROM v_shipment_full ORDER BY awb_number""", con)
assert len(pbi) == 8000
for c in ("Customer Rating", "Transit Days"):
    pbi[c] = pbi[c].astype("Int64")
pbi.to_csv(PBI_CSV, index=False)
print("Power BI file:", PBI_CSV, pbi.shape)
con.close()
