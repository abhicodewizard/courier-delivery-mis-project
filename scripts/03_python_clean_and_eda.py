"""
Stage 3 - Python (Pandas): cleaning + exploratory data analysis (EDA)

Run from the scripts/ folder:  python 03_python_clean_and_eda.py

1. Reads the raw CSV and profiles it
2. Cleans it with the SAME rules used in Excel
3. Validates the clean data and reconciles KPIs with the Excel workbook
4. Saves data/cleaned/courier_shipments_clean.csv  (input for the SQL stage)
5. Runs the delivery-performance analysis with groupby() and saves tables + charts
"""
import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAW = "../data/raw/shipments_raw.csv"
BRANCH = "../data/raw/branch_master.csv"
EXCEL = "../data/cleaned/courier_excel_analysis.xlsx"
OUT_CLEAN = "../data/cleaned/courier_shipments_clean.csv"
EDA_DIR, CHART_DIR = "../outputs/python_eda", "../outputs/charts"
for d in (EDA_DIR, CHART_DIR):
    os.makedirs(d, exist_ok=True)

SLA = {"Express": 2, "Standard": 4, "Economy": 7}      # promised delivery days (business rule)

# ----------------------------------------------------------------------------
# 1. LOAD + PROFILE
# ----------------------------------------------------------------------------
df = pd.read_csv(RAW)
bm = pd.read_csv(BRANCH)
print("=== 1. RAW DATA PROFILE ===")
print("Shape:", df.shape)
print("\nMissing values:\n", df.isna().sum()[df.isna().sum() > 0].to_string())
print("\nExact duplicate rows:", df.duplicated().sum(), "| duplicate AWB numbers:", df["AWB Number"].duplicated().sum())
print("Distinct raw status labels:", df["Status"].nunique(), "| distinct raw destination cities:", df["Destination City"].nunique())
quality = [("Rows in raw file", len(df))]

# ----------------------------------------------------------------------------
# 2. CLEANING
# ----------------------------------------------------------------------------
before = len(df)
df = df.drop_duplicates(subset="AWB Number", keep="first").reset_index(drop=True)
quality.append(("Duplicate rows removed", before - len(df)))

for c in ["Origin City", "Destination City", "Destination State", "Service Type", "Payment Mode", "Status", "Customer Type"]:
    df[c] = df[c].str.strip()

# dates: two text formats -> real dates
for c in ["Booking Date", "Delivery Date"]:
    d1 = pd.to_datetime(df[c], format="%Y-%m-%d", errors="coerce")
    d2 = pd.to_datetime(df[c], format="%d-%m-%Y", errors="coerce")
    df[c] = d1.fillna(d2)
assert df["Booking Date"].notna().all()

# status
s = df["Status"].str.lower()
df["Status"] = np.where(s.str.contains("deliver"), "Delivered",
                        np.where(s.str.contains("rto") | s.str.contains("return"), "RTO", "In Transit"))
df["Service Type"] = df["Service Type"].str.title()

# cities
city_fix = {"bangalore": "Bengaluru", "bombay": "Mumbai", "calcutta": "Kolkata", "new delhi": "Delhi", "madras": "Chennai"}
for c in ["Origin City", "Destination City"]:
    key = df[c].str.lower()
    df[c] = key.map(city_fix).fillna(df[c].str.title())
assert set(df["Origin City"]) | set(df["Destination City"]) <= set(bm["City"]), "unknown city left after cleaning"

# missing destination state -> recover from the destination city (branch master)
state_missing = int(df["Destination State"].isna().sum())
df["Destination State"] = df["Destination State"].fillna(df["Destination City"].map(dict(zip(bm["City"], bm["State"]))))
quality.append(("Missing Destination State recovered from city", state_missing - int(df["Destination State"].isna().sum())))
df["Destination Zone"] = df["Destination City"].map(dict(zip(bm["City"], bm["Zone"])))

# payment mode
p = df["Payment Mode"].str.lower()
df["Payment Mode"] = np.where(p == "cod", "COD", df["Payment Mode"].str.title())
pay_missing = int(df["Payment Mode"].isna().sum())
df["Payment Mode"] = df["Payment Mode"].fillna("Unknown").replace("Nan", "Unknown")
quality.append(("Missing Payment Mode labelled Unknown", int((df["Payment Mode"] == "Unknown").sum())))

# weight entered in grams
grams = int((df["Weight (kg)"] > 100).sum())
df.loc[df["Weight (kg)"] > 100, "Weight (kg)"] = df["Weight (kg)"] / 1000
quality.append(("Weights corrected (grams -> kg)", grams))

# reason: blank means "no issue"
df["Delay/Return Reason"] = df["Delay/Return Reason"].fillna("None")

# ----------------------------------------------------------------------------
# 3. DERIVED COLUMNS
# ----------------------------------------------------------------------------
df["SLA Days"] = df["Service Type"].map(SLA)
df["Transit Days"] = np.where(df["Status"] == "Delivered", (df["Delivery Date"] - df["Booking Date"]).dt.days, np.nan)
df["SLA Status"] = np.where(df["Status"] != "Delivered", "N/A", np.where(df["Transit Days"] <= df["SLA Days"], "On Time", "Late"))
df["Delay Days"] = np.where(df["SLA Status"] == "Late", df["Transit Days"] - df["SLA Days"], 0).astype(int)
df["Booking Year"] = df["Booking Date"].dt.year
df["Booking Quarter"] = "Q" + df["Booking Date"].dt.quarter.astype(str)
df["Booking Month"] = df["Booking Date"].dt.strftime("%Y-%m")
df["Booking Month No"] = df["Booking Date"].dt.month

# ----------------------------------------------------------------------------
# 4. VALIDATION
# ----------------------------------------------------------------------------
assert df["AWB Number"].is_unique
assert df["Weight (kg)"].between(0.05, 60).all(), "weight out of range"
assert df["Freight Amount"].gt(0).all()
assert df.loc[df["Status"] == "Delivered", "Delivery Date"].notna().all(), "delivered shipment without delivery date"
assert df.loc[df["Status"] != "Delivered", "Delivery Date"].isna().all()
assert (df.loc[df["Status"] == "Delivered", "Transit Days"] >= 1).all(), "delivery before booking"
assert set(df["Service Type"]) == set(SLA) and set(df["Status"]) == {"Delivered", "RTO", "In Transit"}
assert df["Customer Rating"].dropna().between(1, 5).all()
for c in df.columns.difference(["Delivery Date", "Transit Days", "Customer Rating"]):
    assert df[c].notna().all(), f"unexpected missing values in {c}"
quality += [("Rows in clean file", len(df)), ("Unrated shipments (blank rating kept)", int(df["Customer Rating"].isna().sum()))]
pd.DataFrame(quality, columns=["Check", "Value"]).to_csv(f"{EDA_DIR}/data_quality_report.csv", index=False)
print("\n=== CLEANING REPORT ===\n", pd.DataFrame(quality, columns=["Check", "Value"]).to_string(index=False))

# ----------------------------------------------------------------------------
# 5. SAVE CLEAN DATA
# ----------------------------------------------------------------------------
cols = ["AWB Number", "Booking Date", "Delivery Date", "Origin City", "Destination City", "Destination State",
        "Destination Zone", "Service Type", "SLA Days", "Weight (kg)", "Freight Amount", "Payment Mode", "COD Amount",
        "Status", "Delivery Attempts", "Delay/Return Reason", "Customer Type", "Customer Rating", "Transit Days",
        "SLA Status", "Delay Days", "Booking Year", "Booking Quarter", "Booking Month", "Booking Month No"]
out = df[cols].copy()
out["Booking Date"] = out["Booking Date"].dt.strftime("%Y-%m-%d")
out["Delivery Date"] = out["Delivery Date"].dt.strftime("%Y-%m-%d")
out["Transit Days"] = out["Transit Days"].astype("Int64")
out["Customer Rating"] = out["Customer Rating"].astype("Int64")
out["Weight (kg)"] = out["Weight (kg)"].round(2)
out.to_csv(OUT_CLEAN, index=False)
print("\nSaved:", OUT_CLEAN, out.shape)

# ----------------------------------------------------------------------------
# 6. KPIs + RECONCILIATION WITH EXCEL
# ----------------------------------------------------------------------------
dl = df[df["Status"] == "Delivered"]
n_deliv, n_rto = len(dl), int((df["Status"] == "RTO").sum())
kpi = {
    "Total Shipments": len(df), "Delivered": n_deliv, "RTO": n_rto, "In Transit": int((df["Status"] == "In Transit").sum()),
    "On-Time Deliveries": int((df["SLA Status"] == "On Time").sum()), "Late Deliveries": int((df["SLA Status"] == "Late").sum()),
    "On-Time Delivery %": round(100 * (df["SLA Status"] == "On Time").sum() / n_deliv, 2),
    "SLA Breach %": round(100 * (df["SLA Status"] == "Late").sum() / n_deliv, 2),
    "Avg Transit Days": round(dl["Transit Days"].mean(), 2),
    "Avg Delay Days (late only)": round(df.loc[df["SLA Status"] == "Late", "Delay Days"].mean(), 2),
    "RTO %": round(100 * n_rto / (n_deliv + n_rto), 2),
    "First-Attempt Delivery %": round(100 * (dl["Delivery Attempts"] == 1).mean(), 2),
    "Total Freight Revenue": int(df["Freight Amount"].sum()), "Avg Freight per Shipment": round(df["Freight Amount"].mean(), 2),
    "Total COD Value": int(df["COD Amount"].sum()), "Avg Customer Rating": round(df["Customer Rating"].mean(), 2),
}
kdf = pd.DataFrame(list(kpi.items()), columns=["KPI", "Value"])
kdf.to_csv(f"{EDA_DIR}/kpis.csv", index=False)
print("\n=== KPIs ===\n", kdf.to_string(index=False))

try:
    import openpyxl
    ws = openpyxl.load_workbook(EXCEL, data_only=True)["Analysis"]
    pairs = [("Total Shipments", "B5", 1), ("Delivered", "B6", 1), ("RTO", "B7", 1), ("On-Time Deliveries", "B9", 1),
             ("On-Time Delivery %", "B11", 100), ("Avg Transit Days", "B13", 1), ("RTO %", "B15", 100),
             ("First-Attempt Delivery %", "B16", 100), ("Total Freight Revenue", "B17", 1), ("Avg Customer Rating", "B20", 1)]
    print("\n=== Reconciliation with Excel ===")
    for name, cell, mult in pairs:
        x, pval = ws[cell].value * mult, kpi[name]
        ok = abs(x - pval) < 0.01
        print(f"{name:28s} Excel={x:>12,.2f}  Python={pval:>12,.2f}  {'MATCH' if ok else 'MISMATCH'}")
        assert ok
except FileNotFoundError:
    print("Excel workbook not found - skipped reconciliation")

# ----------------------------------------------------------------------------
# 7. ANALYSIS WITH groupby()
# ----------------------------------------------------------------------------
def perf(frame, by):
    g = frame.groupby(by)
    t = pd.DataFrame({
        "Shipments": g.size(),
        "Delivered": g.apply(lambda x: (x["Status"] == "Delivered").sum(), include_groups=False),
        "On-Time %": g.apply(lambda x: 100 * (x["SLA Status"] == "On Time").sum() / max((x["Status"] == "Delivered").sum(), 1), include_groups=False),
        "Avg Transit Days": g.apply(lambda x: x.loc[x["Status"] == "Delivered", "Transit Days"].mean(), include_groups=False),
        "RTO %": g.apply(lambda x: 100 * (x["Status"] == "RTO").sum() / max(x["Status"].isin(["Delivered", "RTO"]).sum(), 1), include_groups=False),
        "Freight Revenue": g["Freight Amount"].sum(),
        "Avg Rating": g["Customer Rating"].mean(),
    }).reset_index()
    return t.round(2)


tables = {
    "by_service": perf(df, "Service Type").sort_values("On-Time %"),
    "by_dest_branch": perf(df, "Destination City").sort_values("On-Time %"),
    "by_dest_zone": perf(df, "Destination Zone").sort_values("On-Time %"),
    "by_month": perf(df, "Booking Month"),
    "by_payment_mode": perf(df, "Payment Mode"),
    "by_customer_type": perf(df, "Customer Type"),
}
lanes = df.assign(Lane=df["Origin City"] + " -> " + df["Destination City"])
lane_t = perf(lanes, "Lane")
tables["top_lanes"] = lane_t[lane_t["Shipments"] >= 100].sort_values("Shipments", ascending=False).head(15)
reasons = df[(df["SLA Status"] == "Late") | (df["Status"] == "RTO")]
rs = reasons.groupby(["Delay/Return Reason", "Status"]).size().unstack(fill_value=0)
rs["Total"] = rs.sum(axis=1)
tables["reasons"] = rs.sort_values("Total", ascending=False).reset_index()
tables["rating_by_sla"] = df.groupby("SLA Status")["Customer Rating"].agg(["count", "mean"]).round(2).reset_index()
for name, t in tables.items():
    t.to_csv(f"{EDA_DIR}/{name}.csv", index=False)
for k in ("by_service", "by_dest_branch", "by_payment_mode", "reasons", "rating_by_sla"):
    print(f"\n=== {k} ===\n", tables[k].to_string(index=False))

# seasonality
m = tables["by_month"].copy()
m["Month No"] = m["Booking Month"].str[-2:].astype(int)
season = m.groupby("Month No").apply(lambda x: pd.Series({"Shipments": x["Shipments"].sum()}), include_groups=False)
print("\nWorst 3 months by on-time %:\n", m.sort_values("On-Time %").head(3)[["Booking Month", "Shipments", "On-Time %"]].to_string(index=False))

# ----------------------------------------------------------------------------
# 8. CHARTS
# ----------------------------------------------------------------------------
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
BLUE, GREEN, RED, GREY, ORANGE = "#1F4E79", "#2E8B57", "#C0392B", "#7F8C8D", "#E67E22"

b = tables["by_dest_branch"].sort_values("On-Time %")
fig, ax = plt.subplots(figsize=(8, 5.5))
ax.barh(b["Destination City"], b["On-Time %"], color=[RED if v < 80 else BLUE for v in b["On-Time %"]])
ax.axvline(kpi["On-Time Delivery %"], color="black", ls="--", lw=1)
ax.text(kpi["On-Time Delivery %"] + 0.3, -0.9, f"overall {kpi['On-Time Delivery %']:.1f}%", fontsize=8)
ax.set_xlim(60, 100); ax.set_title("On-Time Delivery % by Destination Branch (red = below 80%)")
fig.tight_layout(); fig.savefig(f"{CHART_DIR}/01_ontime_by_branch.png", dpi=150); plt.close(fig)

mm = tables["by_month"]
fig, ax = plt.subplots(figsize=(11, 4.5))
ax.bar(mm["Booking Month"], mm["Shipments"], color=GREY, alpha=0.6, label="Shipments")
ax.set_ylabel("Shipments"); ax.set_xticks(range(0, len(mm), 2)); ax.set_xticklabels(mm["Booking Month"][::2], rotation=45, ha="right")
ax2 = ax.twinx(); ax2.spines["right"].set_visible(True)
ax2.plot(mm["Booking Month"], mm["On-Time %"], color=RED, marker="o", label="On-Time %")
ax2.set_ylim(60, 100); ax2.set_ylabel("On-Time %"); ax.set_title("Monthly Shipments vs On-Time Delivery %")
fig.tight_layout(); fig.savefig(f"{CHART_DIR}/02_monthly_volume_vs_ontime.png", dpi=150); plt.close(fig)

r = tables["reasons"]
fig, ax = plt.subplots(figsize=(8, 4.5))
bottom = np.zeros(len(r))
for status, color in (("Delivered", ORANGE), ("RTO", RED)):
    vals = r[status].values if status in r.columns else np.zeros(len(r))
    ax.barh(r["Delay/Return Reason"], vals, left=bottom, color=color, label="Late delivery" if status == "Delivered" else "RTO")
    bottom += vals
ax.invert_yaxis(); ax.legend(); ax.set_title("Why shipments are late or returned")
fig.tight_layout(); fig.savefig(f"{CHART_DIR}/03_delay_return_reasons.png", dpi=150); plt.close(fig)

sv = tables["by_service"].set_index("Service Type").loc[["Express", "Standard", "Economy"]].reset_index()
fig, ax = plt.subplots(1, 2, figsize=(9, 4))
ax[0].bar(sv["Service Type"], sv["On-Time %"], color=BLUE); ax[0].set_ylim(60, 100); ax[0].set_title("On-Time % by Service")
ax[1].bar(sv["Service Type"], sv["Avg Transit Days"], color=GREEN); ax[1].set_title("Avg Transit Days by Service")
fig.tight_layout(); fig.savefig(f"{CHART_DIR}/04_service_performance.png", dpi=150); plt.close(fig)

pm = tables["by_payment_mode"]
pm = pm[pm["Payment Mode"] != "Unknown"]
fig, ax = plt.subplots(figsize=(6.5, 4.2))
ax.bar(pm["Payment Mode"], pm["RTO %"], color=[RED if v > 8 else BLUE for v in pm["RTO %"]])
for i, v in enumerate(pm["RTO %"]):
    ax.text(i, v + 0.2, f"{v:.1f}%", ha="center")
ax.set_title("RTO % by Payment Mode")
fig.tight_layout(); fig.savefig(f"{CHART_DIR}/05_rto_by_payment.png", dpi=150); plt.close(fig)

rt = tables["rating_by_sla"]
rt = rt[rt["SLA Status"].isin(["On Time", "Late"])]
fig, ax = plt.subplots(figsize=(5, 4))
ax.bar(rt["SLA Status"], rt["mean"], color=[GREEN, RED]); ax.set_ylim(1, 5); ax.set_title("Average Customer Rating")
for i, v in enumerate(rt["mean"]):
    ax.text(i, v + 0.05, f"{v:.2f}", ha="center")
fig.tight_layout(); fig.savefig(f"{CHART_DIR}/06_rating_vs_sla.png", dpi=150); plt.close(fig)
print("\nCharts saved in", CHART_DIR)
