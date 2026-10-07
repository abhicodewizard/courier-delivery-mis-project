"""
Generates a realistic, slightly messy COURIER SHIPMENT dataset (simulated).
Run from the scripts/ folder:  python 01_generate_raw_dataset.py
Outputs: ../data/raw/shipments_raw.csv / .xlsx  and  ../data/raw/branch_master.csv
The mess is INTENTIONAL, so you can practise cleaning in Excel, Python and SQL.
"""
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

random.seed(11)
np.random.seed(11)
AS_OF = date(2025, 12, 31)          # data snapshot date: shipments not delivered by now are "In Transit"

# ---------------------------------------------------------------- master data
branches = [
    ("B01", "Delhi Hub", "Delhi", "Delhi", "North"),
    ("B02", "Noida Hub", "Noida", "Uttar Pradesh", "North"),
    ("B03", "Meerut Branch", "Meerut", "Uttar Pradesh", "North"),
    ("B04", "Lucknow Hub", "Lucknow", "Uttar Pradesh", "North"),
    ("B05", "Chandigarh Branch", "Chandigarh", "Chandigarh", "North"),
    ("B06", "Jaipur Hub", "Jaipur", "Rajasthan", "West"),
    ("B07", "Mumbai Hub", "Mumbai", "Maharashtra", "West"),
    ("B08", "Pune Branch", "Pune", "Maharashtra", "West"),
    ("B09", "Ahmedabad Hub", "Ahmedabad", "Gujarat", "West"),
    ("B10", "Bengaluru Hub", "Bengaluru", "Karnataka", "South"),
    ("B11", "Chennai Hub", "Chennai", "Tamil Nadu", "South"),
    ("B12", "Hyderabad Hub", "Hyderabad", "Telangana", "South"),
    ("B13", "Kolkata Hub", "Kolkata", "West Bengal", "East"),
    ("B14", "Patna Branch", "Patna", "Bihar", "East"),
    ("B15", "Bhopal Branch", "Bhopal", "Madhya Pradesh", "Central"),
]
bm = pd.DataFrame(branches, columns=["Branch ID", "Branch Name", "City", "State", "Zone"])
bm.to_csv("../data/raw/branch_master.csv", index=False)
zone_of = dict(zip(bm["City"], bm["Zone"]))
state_of = dict(zip(bm["City"], bm["State"]))

# Origins (Chandigarh, Patna and Bhopal only RECEIVE shipments in this data)
origin_w = {"Delhi": 14, "Noida": 10, "Meerut": 10, "Lucknow": 6, "Jaipur": 6, "Mumbai": 14, "Pune": 7,
            "Ahmedabad": 6, "Bengaluru": 12, "Chennai": 6, "Hyderabad": 5, "Kolkata": 4}
dest_w = {"Delhi": 12, "Noida": 6, "Meerut": 5, "Lucknow": 6, "Chandigarh": 4, "Jaipur": 5, "Mumbai": 12,
          "Pune": 7, "Ahmedabad": 6, "Bengaluru": 11, "Chennai": 6, "Hyderabad": 7, "Kolkata": 6,
          "Patna": 4, "Bhopal": 3}
# Some destination branches are weaker operationally (extra chance of a late delivery)
branch_late_adj = {"Patna": 0.12, "Kolkata": 0.08, "Lucknow": 0.05, "Delhi": 0.04, "Mumbai": 0.04,
                   "Bhopal": 0.03, "Chandigarh": -0.03, "Pune": -0.03, "Meerut": -0.03, "Hyderabad": -0.01}

SLA = {"Express": 2, "Standard": 4, "Economy": 7}
BASE_TRANSIT = {  # normal transit days by service and distance class
    "Express": {"city": 1, "zone": 1, "cross": 2},
    "Standard": {"city": 1, "zone": 2, "cross": 3},
    "Economy": {"city": 2, "zone": 3, "cross": 5},
}
RATE_PER_KG = {"Express": 62, "Standard": 38, "Economy": 24}
ZONE_MULT = {"city": 0.8, "zone": 1.0, "cross": 1.3}
SERVICE_LATE_ADJ = {"Express": 0.07, "Standard": 0.0, "Economy": -0.04}
REASONS = ["Hub Congestion", "Weather", "Address Issue", "Customer Unavailable", "Vehicle Breakdown"]

# ---------------------------------------------------------------- booking dates
all_dates = pd.date_range("2024-01-01", "2025-12-31")
month_w = {1: 0.95, 2: 0.9, 3: 1.0, 4: 0.95, 5: 0.95, 6: 0.9, 7: 0.9, 8: 0.95, 9: 1.0, 10: 1.5, 11: 1.4, 12: 1.15}
dw = np.array([month_w[d.month] * (1.12 if d.year == 2025 else 1.0) * (0.5 if d.dayofweek == 6 else 1.0)
               for d in all_dates])
dw = dw / dw.sum()

N = 8000
rows = []
for _ in range(N):
    bdate = pd.Timestamp(np.random.choice(all_dates, p=dw)).date()
    month = bdate.month
    o_city = random.choices(list(origin_w), weights=list(origin_w.values()))[0]
    d_city = random.choices(list(dest_w), weights=list(dest_w.values()))[0]
    service = random.choices(["Express", "Standard", "Economy"], weights=[25, 50, 25])[0]
    ctype = random.choices(["B2C", "B2B"], weights=[65, 35])[0]
    dist = "city" if o_city == d_city else ("zone" if zone_of[o_city] == zone_of[d_city] else "cross")
    sla = SLA[service]

    # payment
    if ctype == "B2C":
        pay = random.choices(["Prepaid", "COD"], weights=[50, 50])[0]
    else:
        pay = random.choices(["Prepaid", "Credit Account"], weights=[35, 65])[0]
    cod_amt = int(round(random.randint(300, 9000), -1)) if pay == "COD" else 0

    # weight and freight
    w = float(np.clip(np.random.lognormal(0.6, 0.8), 0.1, 30)) * (1.8 if ctype == "B2B" else 1.0)
    w = round(min(w, 40), 1)
    freight = int(max(60, RATE_PER_KG[service] * w * ZONE_MULT[dist] * random.uniform(0.95, 1.05)))

    # is it late?
    p_late = 0.10 + branch_late_adj.get(d_city, 0.0) + SERVICE_LATE_ADJ[service] + (0.04 if dist == "cross" else 0.0)
    if month in (10, 11):
        p_late += 0.10          # festive rush
    elif month in (7, 8):
        p_late += 0.06          # monsoon
    elif month in (12, 1):
        p_late += 0.04          # winter fog
    p_late = float(np.clip(p_late, 0.02, 0.6))
    late = random.random() < p_late

    reason = None
    if late:
        extra = random.choices([1, 2, 3, 4], weights=[45, 30, 17, 8])[0]
        transit = sla + extra
        rw = [2, 2, 2, 2, 1]
        if month in (10, 11):
            rw[0] += 5
        if month in (7, 8):
            rw[1] += 5
        if month in (12, 1):
            rw[1] += 3
        reason = random.choices(REASONS, weights=rw)[0]
    else:
        base = BASE_TRANSIT[service][dist]
        transit = min(sla, base + (1 if random.random() < 0.2 else 0))

    attempts = random.choices([1, 2, 3], weights=[90, 8, 2])[0]
    if reason in ("Address Issue", "Customer Unavailable"):
        attempts = random.choices([2, 3], weights=[70, 30])[0]

    # status
    status, ddate = "Delivered", bdate + timedelta(days=int(transit))
    p_rto = 0.025 + (0.05 if pay == "COD" else 0) + (0.02 if ctype == "B2C" else 0)
    if reason in ("Address Issue", "Customer Unavailable"):
        p_rto += 0.20
    if bdate + timedelta(days=int(transit)) > AS_OF:
        status, ddate = "In Transit", None
        reason, attempts = None, 1
    elif random.random() < p_rto:
        status, ddate = "RTO", None
        if reason not in ("Address Issue", "Customer Unavailable"):
            rw = [35, 25, 55 if pay == "COD" else 25]
            reason = random.choices(["Address Issue", "Customer Unavailable", "Customer Refused"], weights=rw)[0]
        attempts = random.choices([2, 3], weights=[30, 70])[0]

    # customer rating (only ~55% of customers rate)
    rating = None
    if status != "In Transit" and random.random() < 0.55:
        if status == "RTO":
            rating = random.choices([1, 2, 3, 4, 5], weights=[30, 30, 25, 10, 5])[0]
        elif late:
            rating = random.choices([1, 2, 3, 4, 5], weights=[20, 22, 30, 20, 8])[0]
        else:
            rating = random.choices([1, 2, 3, 4, 5], weights=[2, 3, 10, 35, 50])[0]

    rows.append({
        "AWB Number": "", "Booking Date": bdate, "Delivery Date": ddate,
        "Origin City": o_city, "Destination City": d_city, "Destination State": state_of[d_city],
        "Service Type": service, "Weight (kg)": w, "Freight Amount": freight, "Payment Mode": pay,
        "COD Amount": cod_amt, "Status": status, "Delivery Attempts": attempts,
        "Delay/Return Reason": reason, "Customer Type": ctype, "Customer Rating": rating,
    })

df = pd.DataFrame(rows).sort_values("Booking Date").reset_index(drop=True)
df["AWB Number"] = [f"TRK{100001 + i}" for i in range(len(df))]
df["Booking Date"] = pd.to_datetime(df["Booking Date"]).dt.strftime("%Y-%m-%d")
df["Delivery Date"] = pd.to_datetime(df["Delivery Date"]).dt.strftime("%Y-%m-%d")   # NaT -> NaN
df["Customer Rating"] = df["Customer Rating"].astype("Int64")

# ---------------------------------------------------------------- inject realistic mess
raw = df.copy()

# 1) Exact duplicate rows (80)
raw = pd.concat([raw, raw.sample(80, random_state=1)], ignore_index=True)

# 2) Mixed date formats: some DD-MM-YYYY
for i in raw.sample(70, random_state=2).index:
    raw.at[i, "Booking Date"] = pd.to_datetime(raw.at[i, "Booking Date"]).strftime("%d-%m-%Y")
dd = raw[raw["Delivery Date"].notna()]
for i in dd.sample(50, random_state=3).index:
    raw.at[i, "Delivery Date"] = pd.to_datetime(raw.at[i, "Delivery Date"], format="%Y-%m-%d", errors="coerce").strftime("%d-%m-%Y") \
        if str(raw.at[i, "Delivery Date"])[4] == "-" else raw.at[i, "Delivery Date"]

# 3) Status labels typed in different ways
variants = {"Delivered": ["delivered", "DELIVERED ", "Delivered "], "RTO": ["Returned", "rto", "RTO ", "Return to Origin"],
            "In Transit": ["in transit", "In-Transit"]}
for i in raw.sample(180, random_state=4).index:
    raw.at[i, "Status"] = random.choice(variants[raw.at[i, "Status"]]) if raw.at[i, "Status"] in variants else raw.at[i, "Status"]

# 4) City spelling / case / space variants (origin and destination)
cv = {"Bengaluru": ["Bangalore", "bengaluru", "BENGALURU"], "Mumbai": ["Bombay", "mumbai"],
      "Kolkata": ["Calcutta", "kolkata "], "Delhi": ["New Delhi", "delhi", " Delhi"], "Chennai": ["Madras", "chennai"],
      "Pune": ["pune"], "Lucknow": ["lucknow "], "Noida": ["noida"], "Meerut": ["meerut "]}
for col, seed in (("Origin City", 5), ("Destination City", 6)):
    for i in raw.sample(150, random_state=seed).index:
        c = raw.at[i, col]
        if c in cv:
            raw.at[i, col] = random.choice(cv[c])

# 5) Service type and payment mode inconsistencies
# (only the TEXT STYLE changes - the underlying value stays the same)
for i in raw.sample(45, random_state=7).index:
    v = raw.at[i, "Service Type"]
    raw.at[i, "Service Type"] = random.choice([v.lower(), v.upper() + " ", v + " "])
for i in raw.sample(50, random_state=8).index:
    v = raw.at[i, "Payment Mode"]
    raw.at[i, "Payment Mode"] = random.choice([v.lower(), v + " ", v.upper()])

# 6) Missing values
for i in raw.sample(40, random_state=9).index:
    raw.at[i, "Destination State"] = np.nan          # recoverable from the destination city
for i in raw.sample(50, random_state=10).index:
    raw.at[i, "Payment Mode"] = np.nan               # cannot be recovered

# 7) Weight entered in GRAMS instead of kg (25 rows)
for i in raw[raw["Weight (kg)"] >= 0.5].sample(25, random_state=11).index:
    raw.at[i, "Weight (kg)"] = raw.at[i, "Weight (kg)"] * 1000

raw = raw.sample(frac=1, random_state=12).reset_index(drop=True)
raw.to_csv("../data/raw/shipments_raw.csv", index=False)
raw.to_excel("../data/raw/shipments_raw.xlsx", index=False, sheet_name="Raw_Data")
print("Raw rows:", len(raw), "| unique AWB:", raw["AWB Number"].nunique())

# quick realism check on the CLEAN version (before mess)
dl = df[df["Status"] == "Delivered"].copy()
dl["transit"] = (pd.to_datetime(dl["Delivery Date"]) - pd.to_datetime(dl["Booking Date"])).dt.days
dl["sla"] = dl["Service Type"].map(SLA)
dl["on_time"] = dl["transit"] <= dl["sla"]
print("\nStatus mix:\n", df["Status"].value_counts().to_string())
print("\nOn-time % overall:", round(100 * dl["on_time"].mean(), 1))
print(dl.groupby("Service Type")["on_time"].mean().mul(100).round(1).to_string())
print(dl.groupby("Destination City")["on_time"].mean().mul(100).round(1).sort_values().head(4).to_string())
closed = df[df["Status"].isin(["Delivered", "RTO"])]
print("\nRTO % of closed:", round(100 * (closed["Status"] == "RTO").mean(), 1))
print(closed.groupby("Payment Mode")["Status"].apply(lambda s: round(100 * (s == "RTO").mean(), 1)).to_string())
