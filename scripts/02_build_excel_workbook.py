"""
Builds the Excel MIS workbook with LIVE formulas.
Run from scripts/ :  python 02_build_excel_workbook.py
Output: ../data/cleaned/courier_excel_analysis.xlsx
(Set env var SAMPLE=300 to build a tiny test file in /tmp - used only to preview charts.)
"""
import os

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SAMPLE = int(os.environ.get("SAMPLE", "0"))
OUT = "/tmp/sample_check.xlsx" if SAMPLE else "../data/cleaned/courier_excel_analysis.xlsx"
os.makedirs("../data/cleaned", exist_ok=True)

raw = pd.read_csv("../data/raw/shipments_raw.csv")
if SAMPLE:
    raw = raw.head(SAMPLE + 20)
bm = pd.read_csv("../data/raw/branch_master.csv")
base = raw.drop_duplicates(subset="AWB Number", keep="first").reset_index(drop=True)   # Excel: Remove Duplicates on AWB
N = len(base)
LAST = N + 1

FONT = "Arial"
HDR = PatternFill("solid", fgColor="1F3864")
FORM = PatternFill("solid", fgColor="375623")
KPI_FILL = PatternFill("solid", fgColor="DDEBF7")
hdr_font = Font(name=FONT, bold=True, color="FFFFFF")
base_font = Font(name=FONT, size=10)
bold = Font(name=FONT, size=10, bold=True)
blue = Font(name=FONT, size=10, color="0000FF")
title_font = Font(name=FONT, size=14, bold=True)


def style_header(ws, row, c1, c2, fill=HDR):
    for c in range(c1, c2 + 1):
        cell = ws.cell(row=row, column=c)
        cell.font, cell.fill = hdr_font, fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def cv(v):
    return None if pd.isna(v) else v


wb = Workbook()

# ------------------------------------------------------------------ README
ws = wb.active
ws.title = "README"
lines = [
    ("Courier Delivery Performance & MIS Dashboard - Excel Workbook", title_font),
    ("", base_font),
    ("Sheet guide", bold),
    ("Excel_Dashboard : KPI tiles + 3 charts (all linked to the Analysis sheet).", base_font),
    ("Analysis        : KPIs, data-quality check and summary tables built with COUNTIFS / SUMIFS / AVERAGEIFS.", base_font),
    ("Clean_Data      : duplicates removed. Columns A-P = original values, columns Q-AF = FORMULAS (green headers).", base_font),
    ("City_Map / Branch_Master / Service_SLA : lookup tables used by the formulas (blue text = hardcoded reference data).", base_font),
    ("Raw_Data        : the original messy file. Never edit this sheet.", base_font),
    ("", base_font),
    ("Definitions", bold),
    ("Transit Days = Delivery Date - Booking Date (Delivered shipments only).", base_font),
    ("SLA Days: Express 2, Standard 4, Economy 7 (assumption stored in Service_SLA). Late = Transit Days > SLA Days.", base_font),
    ("On-Time % = On-time deliveries / Delivered shipments.   RTO % = RTO / (Delivered + RTO)  (In Transit excluded).", base_font),
    ("First-Attempt % = Delivered shipments with 1 attempt / Delivered shipments.", base_font),
    ("", base_font),
    ("Cleaning steps", bold),
    ("1 Remove duplicates on AWB Number   2 Convert two text date formats to real dates   3 Standardise Status, Service and Payment text",
     base_font),
    ("4 Standardise city names with City_Map   5 Fill missing Destination State from the destination city (Branch_Master)", base_font),
    ("6 Weight above 100 kg is treated as a grams-entry error and divided by 1000   7 Missing Payment Mode labelled Unknown", base_font),
]
for i, (t, f) in enumerate(lines, start=1):
    ws.cell(row=i, column=1, value=t).font = f
ws.column_dimensions["A"].width = 135

# ------------------------------------------------------------------ Raw_Data
ws = wb.create_sheet("Raw_Data")
cols = list(raw.columns)
ws.append(cols)
style_header(ws, 1, 1, len(cols))
for r in raw.itertuples(index=False):
    ws.append([cv(v) for v in r])
for c in range(1, len(cols) + 1):
    ws.column_dimensions[get_column_letter(c)].width = 16
ws.freeze_panes = "A2"
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.font = base_font
RAW_LAST = len(raw) + 1

# ------------------------------------------------------------------ Lookups
ws = wb.create_sheet("City_Map")
ws.append(["Variant (lower case, trimmed)", "Standard City"])
style_header(ws, 1, 1, 2)
for a, b in [("bangalore", "Bengaluru"), ("bombay", "Mumbai"), ("calcutta", "Kolkata"),
             ("new delhi", "Delhi"), ("madras", "Chennai")]:
    ws.append([a, b])
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.font = blue
ws["D1"] = "MATCH is not case-sensitive, so 'BANGALORE' also matches 'bangalore'. Other spellings are fixed with TRIM + PROPER."
ws["D1"].font = base_font
ws.column_dimensions["A"].width = 30
ws.column_dimensions["B"].width = 18

ws = wb.create_sheet("Branch_Master")
ws.append(list(bm.columns))
style_header(ws, 1, 1, len(bm.columns))
for r in bm.itertuples(index=False):
    ws.append(list(r))
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.font = blue
for c, w in zip("ABCDE", (10, 20, 14, 18, 10)):
    ws.column_dimensions[c].width = w

ws = wb.create_sheet("Service_SLA")
ws.append(["Service Type", "SLA Days"])
style_header(ws, 1, 1, 2)
for a, b in [("Express", 2), ("Standard", 4), ("Economy", 7)]:
    ws.append([a, b])
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.font = blue
ws["D1"] = "Assumption: promised delivery time in days per service type (simulated business rule)."
ws["D1"].font = base_font
ws.column_dimensions["A"].width = 16

# ------------------------------------------------------------------ Clean_Data
ws = wb.create_sheet("Clean_Data")
orig_cols = list(raw.columns)                       # A..P
fcols = ["Booking Date (Clean)", "Delivery Date (Clean)", "Status (Clean)", "Service (Clean)", "Origin City (Clean)",
         "Dest City (Clean)", "Dest State (Clean)", "Dest Zone", "Weight kg (Clean)", "Payment (Clean)", "Transit Days",
         "SLA Days", "SLA Status", "Delay Days", "Booking Month", "Booking Year"]       # Q..AF
ws.append(orig_cols + fcols)
style_header(ws, 1, 1, len(orig_cols))
style_header(ws, 1, len(orig_cols) + 1, len(orig_cols) + len(fcols), fill=FORM)


def date_f(cell):
    return (f'IF(MID({cell},5,1)="-",DATE(VALUE(LEFT({cell},4)),VALUE(MID({cell},6,2)),VALUE(RIGHT({cell},2))),'
            f'DATE(VALUE(RIGHT({cell},4)),VALUE(MID({cell},4,2)),VALUE(LEFT({cell},2))))')


def city_f(cell):
    return f'IFERROR(INDEX(City_Map!$B$2:$B$6,MATCH(TRIM({cell}),City_Map!$A$2:$A$6,0)),PROPER(TRIM({cell})))'


for i, r in enumerate(base.itertuples(index=False), start=2):
    f = [
        f'={date_f(f"B{i}")}',                                                                         # Q
        f'=IF(TRIM(C{i})="","",{date_f(f"C{i}")})',                                                    # R
        f'=IF(ISNUMBER(SEARCH("deliver",L{i})),"Delivered",IF(OR(ISNUMBER(SEARCH("rto",L{i})),ISNUMBER(SEARCH("return",L{i}))),"RTO","In Transit"))',  # S
        f'=PROPER(TRIM(G{i}))',                                                                        # T
        f'={city_f(f"D{i}")}',                                                                         # U
        f'={city_f(f"E{i}")}',                                                                         # V
        f'=IF(TRIM(F{i})="",IFERROR(INDEX(Branch_Master!$D$2:$D$16,MATCH(V{i},Branch_Master!$C$2:$C$16,0)),"Unknown"),TRIM(F{i}))',  # W
        f'=IFERROR(INDEX(Branch_Master!$E$2:$E$16,MATCH(V{i},Branch_Master!$C$2:$C$16,0)),"Unknown")',  # X
        f'=IF(H{i}>100,H{i}/1000,H{i})',                                                               # Y
        f'=IF(TRIM(J{i})="","Unknown",IF(LOWER(TRIM(J{i}))="cod","COD",PROPER(TRIM(J{i}))))',          # Z
        f'=IF(S{i}="Delivered",R{i}-Q{i},"")',                                                         # AA
        f'=INDEX(Service_SLA!$B$2:$B$4,MATCH(T{i},Service_SLA!$A$2:$A$4,0))',                          # AB
        f'=IF(S{i}<>"Delivered","N/A",IF(AA{i}<=AB{i},"On Time","Late"))',                             # AC
        f'=IF(AC{i}="Late",AA{i}-AB{i},0)',                                                            # AD
        f'=AF{i}&"-"&TEXT(MONTH(Q{i}),"00")',                                                          # AE
        f'=YEAR(Q{i})',                                                                                # AF
    ]
    ws.append([cv(v) for v in r] + f)

for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.font = base_font
    row[16].number_format = "dd-mmm-yyyy"      # Q
    row[17].number_format = "dd-mmm-yyyy"      # R
for c in range(1, len(orig_cols) + len(fcols) + 1):
    ws.column_dimensions[get_column_letter(c)].width = 16
ws.freeze_panes = "B2"
ws.auto_filter.ref = f"A1:{get_column_letter(len(orig_cols) + len(fcols))}{LAST}"

rng = lambda col: f"Clean_Data!${col}$2:${col}${LAST}"

# ------------------------------------------------------------------ Analysis
ws = wb.create_sheet("Analysis")
ws["A1"] = "Delivery Performance Analysis (all values are formulas on Clean_Data)"
ws["A1"].font = title_font


def put_header(row, labels, col=1):
    for j, h in enumerate(labels):
        ws.cell(row=row, column=col + j, value=h)
    style_header(ws, row, col, col + len(labels) - 1)


def fmt(cell, nf=None, font=base_font):
    cell.font = font
    if nf:
        cell.number_format = nf


ws["A3"] = "1. KPIs"
ws["A3"].font = bold
put_header(4, ["KPI", "Value", "How it is calculated"])
kpis = [
    ("Total Shipments", f'=COUNTA({rng("A")})', "#,##0", "Count of AWB numbers"),                     # 5
    ("Delivered", f'=COUNTIF({rng("S")},"Delivered")', "#,##0", "Status = Delivered"),                 # 6
    ("RTO (Returned)", f'=COUNTIF({rng("S")},"RTO")', "#,##0", "Status = RTO"),                       # 7
    ("In Transit", f'=COUNTIF({rng("S")},"In Transit")', "#,##0", "Status = In Transit"),             # 8
    ("On-Time Deliveries", f'=COUNTIF({rng("AC")},"On Time")', "#,##0", "Transit Days <= SLA Days"),  # 9
    ("Late Deliveries", f'=COUNTIF({rng("AC")},"Late")', "#,##0", "Transit Days > SLA Days"),         # 10
    ("On-Time Delivery %", "=B9/B6", "0.0%", "On-Time / Delivered"),                                  # 11
    ("SLA Breach %", "=B10/B6", "0.0%", "Late / Delivered"),                                          # 12
    ("Avg Transit Days", f'=AVERAGE({rng("AA")})', "0.00", "Average of Transit Days (delivered)"),    # 13
    ("Avg Delay Days (late only)", f'=AVERAGEIF({rng("AC")},"Late",{rng("AD")})', "0.00", "Average delay of late shipments"),  # 14
    ("RTO %", "=B7/(B6+B7)", "0.0%", "RTO / (Delivered + RTO)"),                                      # 15
    ("First-Attempt Delivery %", f'=COUNTIFS({rng("S")},"Delivered",{rng("M")},1)/B6', "0.0%", "Delivered in 1 attempt / Delivered"),  # 16
    ("Total Freight Revenue (INR)", f'=SUM({rng("I")})', "#,##0", "Sum of Freight Amount"),             # 17
    ("Avg Freight per Shipment (INR)", "=B17/B5", "#,##0", "Revenue / Shipments"),                    # 18
    ("Total COD Value (INR)", f'=SUM({rng("K")})', "#,##0", "Sum of COD Amount"),                     # 19
    ("Avg Customer Rating", f'=AVERAGE({rng("P")})', "0.00", "Average of ratings given (blank = not rated)"),  # 20
]
for k, (lab, fml, nf, note) in enumerate(kpis):
    r = 5 + k
    ws.cell(row=r, column=1, value=lab)
    ws.cell(row=r, column=2, value=fml)
    ws.cell(row=r, column=3, value=note)
    fmt(ws.cell(row=r, column=1)); fmt(ws.cell(row=r, column=2), nf, bold); fmt(ws.cell(row=r, column=3))

ws["E3"] = "Data quality check"
ws["E3"].font = bold
put_header(4, ["Check", "Value"], col=5)
dq = [
    ("Rows in Raw_Data", f"=COUNTA(Raw_Data!$A$2:$A${RAW_LAST})"),
    ("Rows after removing duplicates", "=B5"),
    ("Duplicate rows removed", "=F5-F6"),
    ("Weights entered in grams (>100)", f'=COUNTIF({rng("H")},">100")'),
    ("Missing Destination State", f'=COUNTBLANK({rng("F")})'),
    ("Missing Payment Mode", f'=COUNTBLANK({rng("J")})'),
]
for k, (lab, fml) in enumerate(dq):
    r = 5 + k
    ws.cell(row=r, column=5, value=lab)
    ws.cell(row=r, column=6, value=fml)
    fmt(ws.cell(row=r, column=5)); fmt(ws.cell(row=r, column=6), "#,##0", bold)

POS = {}


def block(name, title, start, key_label, keys, key_col):
    ws.cell(row=start, column=1, value=title).font = bold
    put_header(start + 1, [key_label, "Shipments", "Delivered", "On-Time %", "Avg Transit Days", "RTO %",
                           "Freight Revenue", "Avg Rating"])
    first = start + 2
    for k, key in enumerate(keys):
        r = first + k
        K = rng(key_col)
        ws.cell(row=r, column=1, value=key)
        ws.cell(row=r, column=2, value=f'=COUNTIFS({K},$A{r})')
        ws.cell(row=r, column=3, value=f'=COUNTIFS({K},$A{r},{rng("S")},"Delivered")')
        ws.cell(row=r, column=4, value=f'=IF(C{r}=0,0,COUNTIFS({K},$A{r},{rng("AC")},"On Time")/C{r})')
        ws.cell(row=r, column=5, value=f'=IFERROR(AVERAGEIFS({rng("AA")},{K},$A{r},{rng("S")},"Delivered"),0)')
        ws.cell(row=r, column=6, value=f'=IFERROR(COUNTIFS({K},$A{r},{rng("S")},"RTO")/(C{r}+COUNTIFS({K},$A{r},{rng("S")},"RTO")),0)')
        ws.cell(row=r, column=7, value=f'=SUMIFS({rng("I")},{K},$A{r})')
        ws.cell(row=r, column=8, value=f'=IFERROR(AVERAGEIFS({rng("P")},{K},$A{r}),0)')
        fmt(ws.cell(row=r, column=1))
        for c, nf in ((2, "#,##0"), (3, "#,##0"), (4, "0.0%"), (5, "0.00"), (6, "0.0%"), (7, "#,##0"), (8, "0.00")):
            fmt(ws.cell(row=r, column=c), nf)
    POS[name] = (first, first + len(keys) - 1)
    return first + len(keys)


services = ["Express", "Standard", "Economy"]
dest_cities = list(bm["City"])
zones = ["North", "West", "South", "East", "Central"]
months = sorted({(f"{d[:4]}-{d[5:7]}" if d[4] == "-" else f"{d[6:]}-{d[3:5]}") for d in base["Booking Date"]})
pays = ["Prepaid", "COD", "Credit Account", "Unknown"]
ctypes = ["B2C", "B2B"]

row = 24
row = block("service", "2. Service type", row, "Service", services, "T") + 2
row = block("branch", "3. Destination branch (city)", row, "Destination City", dest_cities, "V") + 2
row = block("zone", "4. Destination zone", row, "Zone", zones, "X") + 2
row = block("month", "5. Month", row, "Booking Month", months, "AE") + 2
row = block("pay", "6. Payment mode", row, "Payment Mode", pays, "Z") + 2
row = block("ctype", "7. Customer type", row, "Customer Type", ctypes, "O") + 2

ws.cell(row=row, column=1, value="8. Delay and return reasons").font = bold
put_header(row + 1, ["Reason", "Late Deliveries", "RTO Shipments", "Total"])
reasons = ["Hub Congestion", "Weather", "Address Issue", "Customer Unavailable", "Vehicle Breakdown", "Customer Refused"]
first = row + 2
for k, rs in enumerate(reasons):
    r = first + k
    ws.cell(row=r, column=1, value=rs)
    ws.cell(row=r, column=2, value=f'=COUNTIFS({rng("N")},$A{r},{rng("AC")},"Late")')
    ws.cell(row=r, column=3, value=f'=COUNTIFS({rng("N")},$A{r},{rng("S")},"RTO")')
    ws.cell(row=r, column=4, value=f'=B{r}+C{r}')
    fmt(ws.cell(row=r, column=1))
    for c in (2, 3, 4):
        fmt(ws.cell(row=r, column=c), "#,##0")
POS["reason"] = (first, first + len(reasons) - 1)

for c, w in zip("ABCDEFGH", (34, 16, 16, 14, 18, 12, 16, 12)):
    ws.column_dimensions[c].width = w
ws.column_dimensions["C"].width = 40

# ------------------------------------------------------------------ Excel_Dashboard
ws = wb.create_sheet("Excel_Dashboard")
ws.sheet_view.showGridLines = False
ws["A1"] = "Courier Delivery Performance - MIS Dashboard"
ws["A1"].font = Font(name=FONT, size=18, bold=True, color="1F3864")
ws["A2"] = "Simulated data, Jan 2024 - Dec 2025. All tiles and charts are linked to the Analysis sheet."
ws["A2"].font = Font(name=FONT, size=9, italic=True)
tiles = [("Total Shipments", "B5", "#,##0"), ("On-Time Delivery %", "B11", "0.0%"), ("Avg Transit Days", "B13", "0.00"),
         ("RTO %", "B15", "0.0%"), ("First-Attempt %", "B16", "0.0%"), ("Freight Revenue (INR)", "B17", "#,##0")]
for k, (lab, ref, nf) in enumerate(tiles):
    c = 1 + k * 2
    ws.cell(row=4, column=c, value=lab).font = Font(name=FONT, size=9, bold=True, color="1F3864")
    ws.cell(row=5, column=c, value=f"=Analysis!{ref}")
    v = ws.cell(row=5, column=c)
    v.font = Font(name=FONT, size=18, bold=True)
    v.number_format = nf
    for rr in (4, 5):
        for cc in (c, c + 1):
            ws.cell(row=rr, column=cc).fill = KPI_FILL
    ws.merge_cells(start_row=4, start_column=c, end_row=4, end_column=c + 1)
    ws.merge_cells(start_row=5, start_column=c, end_row=5, end_column=c + 1)
    ws.cell(row=5, column=c).alignment = Alignment(horizontal="left")
for c in range(1, 13):
    ws.column_dimensions[get_column_letter(c)].width = 13

an = wb["Analysis"]


def chart_refs(name, val_col, cat_col=1):
    a, b = POS[name]
    return Reference(an, min_col=val_col, min_row=a - 1, max_row=b), Reference(an, min_col=cat_col, min_row=a, max_row=b)


# Chart 1: on-time % by destination branch
ch1 = BarChart(); ch1.type = "col"; ch1.title = "On-Time Delivery % by Destination Branch"
d, c = chart_refs("branch", 4); ch1.add_data(d, titles_from_data=True); ch1.set_categories(c)
ch1.y_axis.numFmt = "0%"; ch1.y_axis.scaling.min = 0.6; ch1.y_axis.scaling.max = 1.0; ch1.legend = None
ch1.height, ch1.width = 7.5, 17
ws.add_chart(ch1, "A8")
# Chart 2: monthly on-time %
ch2 = LineChart(); ch2.title = "Monthly On-Time Delivery %"
d, c = chart_refs("month", 4); ch2.add_data(d, titles_from_data=True); ch2.set_categories(c)
ch2.y_axis.numFmt = "0%"; ch2.y_axis.scaling.min = 0.6; ch2.y_axis.scaling.max = 1.0; ch2.legend = None
ch2.height, ch2.width = 7.5, 17
ws.add_chart(ch2, "H8")
# Chart 3: delay / return reasons
ch3 = BarChart(); ch3.type = "bar"; ch3.title = "Delay & Return Reasons (count)"
a, b = POS["reason"]
ch3.add_data(Reference(an, min_col=4, min_row=a - 1, max_row=b), titles_from_data=True)
ch3.set_categories(Reference(an, min_col=1, min_row=a, max_row=b)); ch3.legend = None
ch3.height, ch3.width = 7.5, 17
ws.add_chart(ch3, "A24")
# Chart 4: on-time % by service
ch4 = BarChart(); ch4.type = "col"; ch4.title = "On-Time Delivery % by Service"
d, c = chart_refs("service", 4); ch4.add_data(d, titles_from_data=True); ch4.set_categories(c)
ch4.y_axis.numFmt = "0%"; ch4.y_axis.scaling.min = 0.6; ch4.y_axis.scaling.max = 1.0; ch4.legend = None
ch4.height, ch4.width = 7.5, 17
ws.add_chart(ch4, "H24")

wb._sheets = [wb["README"], wb["Excel_Dashboard"], wb["Analysis"], wb["Clean_Data"], wb["City_Map"],
              wb["Branch_Master"], wb["Service_SLA"], wb["Raw_Data"]]
wb.save(OUT)
print("saved", OUT, "| clean rows:", N)
