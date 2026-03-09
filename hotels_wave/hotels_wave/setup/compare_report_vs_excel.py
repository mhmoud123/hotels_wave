"""
Compare Overbooking Calendar report output vs Excel DailyCalendar.
Run: bench --site hotels.site execute hotels_wave.hotels_wave.setup.compare_report_vs_excel.run
"""
import frappe

HOTEL = "الفندق التجريبي"
UNIT_TYPE = "غرفة ثنائية"

# Excel DailyCalendar values for غرفة ثنائية Feb 2026
EXCEL = {
    "2026-02-01": {"in_house": 60, "arrivals": 30, "expected": 116.0,  "sellable": 175, "adj_occ": 77.3,  "risk": "LOW"},
    "2026-02-02": {"in_house": 62, "arrivals": 2,  "expected": 140.4,  "sellable": 175, "adj_occ": 93.6,  "risk": "HIGH"},
    "2026-02-03": {"in_house": 63, "arrivals": 1,  "expected": 142.2,  "sellable": 175, "adj_occ": 94.8,  "risk": "HIGH"},
    "2026-02-04": {"in_house": 66, "arrivals": 3,  "expected": 143.6,  "sellable": 175, "adj_occ": 95.7,  "risk": "HIGH"},
    "2026-02-05": {"in_house": 73, "arrivals": 7,  "expected": 156.7,  "sellable": 160, "adj_occ": 104.5, "risk": "HIGH"},
    "2026-02-06": {"in_house": 74, "arrivals": 1,  "expected": 163.1,  "sellable": 160, "adj_occ": 108.7, "risk": "HIGH"},
    "2026-02-07": {"in_house": 75, "arrivals": 1,  "expected": 154.2,  "sellable": 175, "adj_occ": 102.8, "risk": "HIGH"},
    "2026-02-08": {"in_house": 79, "arrivals": 4,  "expected": 155.8,  "sellable": 175, "adj_occ": 103.9, "risk": "HIGH"},
    "2026-02-09": {"in_house": 23, "arrivals": 4,  "expected": 99.8,   "sellable": 175, "adj_occ": 66.5,  "risk": "LOW"},
    "2026-02-10": {"in_house": 21, "arrivals": 0,  "expected": 101.0,  "sellable": 175, "adj_occ": 67.3,  "risk": "LOW"},
}


def run():
    from hotels_wave.hotels_wave.report.overbooking_calendar.overbooking_calendar import execute as run_report

    filters = {
        "hotel": HOTEL,
        "unit_type": UNIT_TYPE,
        "from_date": "2026-02-01",
        "to_date": "2026-02-10",
    }

    columns, data = run_report(filters)

    print("\n=== COLUMN NAMES IN REPORT ===")
    for c in columns:
        print(f"  {c['fieldname']:30} {c['label']}")

    print("\n=== REPORT DATA vs EXCEL (Feb 1-10) ===")
    print(f"{'Date':<12} {'Booked':>6} {'InHse':>6} {'Arriv':>6} {'ExpOcc':>8} {'Sell':>5} {'Occ%':>6} {'Risk':<7}  |  Excel IH  Arr  Exp  Occ%  Risk")
    print("-" * 105)

    for row in data:
        d = row["date"]
        ex = EXCEL.get(d, {})
        ih = row.get("in_house_arrivals", "N/A")
        ar = row.get("arrivals", "N/A")
        exp = row.get("expected_occupied", "N/A")
        sell = row.get("sellable_rooms", "?")
        occ = row.get("adj_occupancy_pct", "?")
        risk = row.get("risk_level", "?")
        bk = row.get("booked_rooms", "?")

        if ex:
            print(f"{d:<12} {bk:>6} {str(ih):>6} {str(ar):>6} {str(round(float(exp),1) if exp!='N/A' else 'N/A'):>8} {sell:>5} {str(round(float(occ),1) if occ!='?' else '?'):>6} {risk:<7}  |  "
                  f"{ex['in_house']:>4} {ex['arrivals']:>4} {ex['expected']:>5.1f} {ex['adj_occ']:>5.1f}% {ex['risk']}")
        else:
            print(f"{d:<12} {bk:>6} {str(ih):>6} {str(ar):>6} {str(round(float(exp),1) if exp!='N/A' else 'N/A'):>8} {sell:>5} {occ:>6} {risk:<7}")
