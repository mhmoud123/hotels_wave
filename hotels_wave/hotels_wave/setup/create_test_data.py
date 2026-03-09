# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

"""
Create full test data from the Excel reference file
(نموذج التسعير الفندقي المتقدم.xlsx) so reports can be verified.

Run:
    bench --site hotels.site execute hotels_wave.hotels_wave.setup.create_test_data.run

To wipe and recreate everything:
    bench --site hotels.site execute hotels_wave.hotels_wave.setup.create_test_data.reset_and_run
"""

import frappe
from frappe.utils import getdate


# ---------------------------------------------------------------------------
# Configuration from Excel
# ---------------------------------------------------------------------------
HOTEL_NAME = "الفندق التجريبي"
HOTEL_CUSTOMER_NAME = "الفندق التجريبي"

UNIT_TYPES = {
    "غرفة ثنائية": {"total_units": 150, "cost_per_night": 35.94, "markup_pct": 50},
    "غرفة ثلاثية": {"total_units": 100, "cost_per_night": 36.14, "markup_pct": 60},
    "غرفة رباعية": {"total_units": 100, "cost_per_night": 36.64, "markup_pct": 70},
    "جناح":         {"total_units": 100, "cost_per_night": 41.14, "markup_pct": 80},
}

OTA_BOOKING_NAME = "الفندق التجريبي-Booking.com"

SEASONS = [
    ("Umrah Season",          "2026-01-01", "2026-02-17", 1.3),
    ("First - 10 - Ramadan",  "2026-02-18", "2026-02-27", 2.0),
    ("Middle - 10 - Ramadan", "2026-02-28", "2026-03-09", 2.2),
    ("Last - 10 - Ramadan",   "2026-03-10", "2026-03-19", 4.0),
]

# ReservationsToDay (11 records from Excel)
HOTEL_RESERVATIONS = [
    # unit_type, status, check_in_status, booking_source, rental_type, check_in, check_out, rooms
    ("غرفة ثنائية", "مؤكد", "تسجيل دخول", "Booking",  "يومي", "2026-01-31", "2026-02-09", 30),
    ("غرفة ثنائية", "مؤكد", "تسجيل دخول", "Booking",  "يومي", "2026-02-01", "2026-02-09", 30),
    ("غرفة ثنائية", "مؤكد", "تسجيل دخول", "Booking",  "يومي", "2026-02-02", "2026-02-10",  2),
    ("غرفة ثنائية", "مؤكد", "تسجيل دخول", "Booking",  "يومي", "2026-02-03", "2026-02-11",  1),
    ("غرفة ثنائية", "مؤكد", "تسجيل دخول", "Booking",  "يومي", "2026-02-04", "2026-02-12",  1),
    ("غرفة ثنائية", "مؤكد", "تسجيل دخول", "Booking",  "يومي", "2026-02-05", "2026-02-13",  7),
    ("غرفة ثنائية", "مؤكد", "تسجيل دخول", "Booking",  "يومي", "2026-02-06", "2026-02-14",  1),
    ("غرفة ثنائية", "مؤكد", "تسجيل دخول", "اخرى",    "يومي", "2026-02-07", "2026-02-15",  1),
    ("غرفة ثنائية", "مؤكد", "تسجيل دخول", "اخرى",    "يومي", "2026-02-04", "2026-02-19",  2),
    ("غرفة ثنائية", "مؤكد", "تسجيل دخول", "استقبال", "يومي", "2026-02-08", "2026-02-16",  4),
    ("غرفة ثنائية", "مؤكد", "تسجيل دخول", "استقبال", "يومي", "2026-02-09", "2026-02-17",  4),
]


# ---------------------------------------------------------------------------
# Main Entry Points
# ---------------------------------------------------------------------------

def run():
    """Create all test data — skip if already exists."""
    print("Creating test data from Excel reference...")
    _create_unit_types()
    _create_hotel_customer()
    _create_ota_account()
    _create_hotel_unit_type()
    _create_hotel_seasons()
    _create_demand_pressure_factors()
    _create_hotel_cost_structure()
    _create_hotel_pricing_config()
    _seed_factor_tables()
    _create_hotel_reservations()
    _create_booking_intake()
    frappe.db.commit()
    print("\n✅  Test data created successfully.")
    print("   Run the Dynamic Pricing Dashboard for Feb 2026 to verify against Excel.")


def reset_and_run():
    """Delete all test data and recreate from scratch."""
    print("Resetting test data...")
    _delete_test_data()
    frappe.db.commit()
    run()


# ---------------------------------------------------------------------------
# Creators
# ---------------------------------------------------------------------------

def _create_unit_types():
    for name in UNIT_TYPES:
        if not frappe.db.exists("Unit Type", name):
            frappe.get_doc({"doctype": "Unit Type", "type_name": name}).insert(ignore_permissions=True)
    print("  → Unit Types: OK")


def _create_hotel_customer():
    if not frappe.db.exists("Customer", HOTEL_CUSTOMER_NAME):
        frappe.get_doc({
            "doctype": "Customer",
            "customer_name": HOTEL_CUSTOMER_NAME,
            "customer_type": "Company",
            "custom_is_hotel_entity": 1,
            "custom_hotel_name": HOTEL_NAME,
        }).insert(ignore_permissions=True)
        print(f"  → Customer created: {HOTEL_CUSTOMER_NAME}")
    else:
        # Make sure custom_is_hotel_entity is set
        frappe.db.set_value("Customer", HOTEL_CUSTOMER_NAME, "custom_is_hotel_entity", 1)
        frappe.db.set_value("Customer", HOTEL_CUSTOMER_NAME, "custom_hotel_name", HOTEL_NAME)
        print(f"  → Customer already exists: {HOTEL_CUSTOMER_NAME}")


def _create_ota_account():
    if not frappe.db.exists("OTA Account Setup", OTA_BOOKING_NAME):
        frappe.get_doc({
            "doctype": "OTA Account Setup",
            "hotel": HOTEL_CUSTOMER_NAME,
            "ota_name": "Booking.com",
            "connection_type": "Manual",
            "channel_type": "OTA",
            "platform_commission": 15,
            "channel_discount_pct": 5,
            "no_show_rate_weekday": 20,    # 20% from Excel
            "no_show_rate_weekend": 10,    # 10% from Excel (Thu/Fri Gulf)
        }).insert(ignore_permissions=True)
        print(f"  → OTA Account created: {OTA_BOOKING_NAME}")
    else:
        print(f"  → OTA Account already exists: {OTA_BOOKING_NAME}")


def _create_hotel_unit_type():
    hut_name = frappe.db.get_value("Hotel Unit Type", {"hotel": HOTEL_CUSTOMER_NAME}, "name")
    if not hut_name:
        details = []
        # Set units_allowed_on_platforms = total_units initially (all available)
        for ut_name, cfg in UNIT_TYPES.items():
            details.append({
                "doctype": "Hotel Unit Detail",
                "unit_type_ref": ut_name,
                "total_units": cfg["total_units"],
                "units_allowed_on_platforms": cfg["total_units"],
                "overbooked": 0,
            })
        frappe.get_doc({
            "doctype": "Hotel Unit Type",
            "hotel": HOTEL_CUSTOMER_NAME,
            "units_list": details,
        }).insert(ignore_permissions=True)
        print("  → Hotel Unit Type created with details")
    else:
        print(f"  → Hotel Unit Type already exists: {hut_name}")


def _create_hotel_seasons():
    for name, start, end, factor in SEASONS:
        if not frappe.db.exists("Hotel Season", {"hotel": HOTEL_CUSTOMER_NAME, "season_name_label": name}):
            frappe.get_doc({
                "doctype": "Hotel Season",
                "hotel": HOTEL_CUSTOMER_NAME,
                "season_name_label": name,
                "start_date": start,
                "end_date": end,
                "season_factor": factor,
            }).insert(ignore_permissions=True)
    print(f"  → Hotel Seasons: {len(SEASONS)} created")


def _create_demand_pressure_factors():
    rows = [
        # min_occ  max_occ  factor  (from DailyCalendar/OverbookingControl pattern)
        (  0,   50,  1.00),
        ( 50,   60,  1.00),
        ( 60,   70,  1.00),
        ( 70,   80,  1.00),
        ( 80,   90,  1.10),
        ( 90,  100,  1.20),
        (100,  200,  1.50),
    ]
    created = 0
    for min_o, max_o, factor in rows:
        existing = frappe.get_all("Demand Pressure Factor",
                                   filters={"min_occupancy_pct": min_o, "max_occupancy_pct": max_o})
        if not existing:
            frappe.get_doc({
                "doctype": "Demand Pressure Factor",
                "min_occupancy_pct": min_o,
                "max_occupancy_pct": max_o,
                "factor": factor,
            }).insert(ignore_permissions=True)
            created += 1
    print(f"  → Demand Pressure Factors: {created} created")


def _create_hotel_cost_structure():
    existing = frappe.db.get_value("Hotel Cost Structure", {"hotel": HOTEL_CUSTOMER_NAME}, "name")
    if existing:
        print(f"  → Hotel Cost Structure already exists: {existing}")
        return

    # From FixedAndVariableCosts sheet
    # (cost_category, description, monthly_amount, cost_per_room_per_night, unit_type, cost_type)
    # cost_category must be one of: Staff, Utilities, Supplies, Maintenance, Other
    cost_items = [
        ("Staff",       "عمال",           10000, 0.7407,  None,             "Fixed"),
        ("Staff",       "استقبال",         8000,  0.5926,  None,             "Fixed"),
        ("Staff",       "مدراء",           10000, 0.7407,  None,             "Fixed"),
        ("Staff",       "محاسب",           4000,  0.2963,  None,             "Fixed"),
        ("Staff",       "موظفين حجوزات",   4000,  0.2963,  None,             "Fixed"),
        ("Staff",       "حراس امن",        3000,  0.2222,  None,             "Fixed"),
        ("Other",       "مواقف",           2000,  0.1481,  None,             "Fixed"),
        ("Staff",       "سواقين",          2000,  0.1481,  None,             "Fixed"),
        ("Other",       "الباصات",         34500, 2.5556,  None,             "Fixed"),
        ("Supplies",    "ضيافة الغرف",     4.8,   4.8,     "غرفة ثنائية",    "Variable"),
        ("Supplies",    "ضيافة الغرف",     5.0,   5.0,     "غرفة ثلاثية",    "Variable"),
        ("Supplies",    "ضيافة الغرف",     5.5,   5.5,     "غرفة رباعية",    "Variable"),
        ("Supplies",    "ضيافة الغرف",     10.0,  10.0,    "جناح",            "Variable"),
        ("Supplies",    "غسيل الشراشف",    12.4,  12.4,    "غرفة ثنائية",    "Variable"),
        ("Supplies",    "غسيل الشراشف",    12.4,  12.4,    "غرفة ثلاثية",    "Variable"),
        ("Supplies",    "غسيل الشراشف",    12.4,  12.4,    "غرفة رباعية",    "Variable"),
        ("Supplies",    "غسيل الشراشف",    12.4,  12.4,    "جناح",            "Variable"),
        ("Utilities",   "الكهرباء",        10.0,  10.0,    None,             "Variable"),
        ("Utilities",   "الماء",            0.5,   0.5,    None,             "Variable"),
        ("Supplies",    "مواد النظافة",     2.5,   2.5,    None,             "Variable"),
    ]

    items_docs = []
    for cat, desc, monthly, cpn, ut, ctype in cost_items:
        items_docs.append({
            "doctype": "Hotel Cost Item",
            "cost_category": cat,
            "description": desc,
            "monthly_amount": monthly,
            "cost_per_room_per_night": cpn,
            "unit_type": ut,
            "cost_type": ctype,
        })

    frappe.get_doc({
        "doctype": "Hotel Cost Structure",
        "hotel": HOTEL_CUSTOMER_NAME,
        "effective_date": "2026-01-01",
        "cost_items": items_docs,
    }).insert(ignore_permissions=True)
    print("  → Hotel Cost Structure created")


def _create_hotel_pricing_config():
    existing = frappe.db.get_value("Hotel Pricing Config", {"hotel": HOTEL_CUSTOMER_NAME}, "name")
    if existing:
        print(f"  → Hotel Pricing Config already exists: {existing}")
        return

    room_pricing = []
    for ut_name, cfg in UNIT_TYPES.items():
        suggested = cfg["cost_per_night"] * (1 + cfg["markup_pct"] / 100)
        room_pricing.append({
            "doctype": "Hotel Room Type Pricing",
            "unit_type": ut_name,
            "cost_per_night": cfg["cost_per_night"],
            "markup_pct": cfg["markup_pct"],
            "suggested_price": round(suggested, 4),
        })

    frappe.get_doc({
        "doctype": "Hotel Pricing Config",
        "hotel": HOTEL_CUSTOMER_NAME,
        "is_active": 1,
        "safety_buffer_rate": 3,       # 3% from Excel
        "lock_threshold_pct": 90,      # 90% from Excel
        "min_margin_pct": 25,          # 25% from ProfitMargins
        "min_profit_per_night": 10,    # 10 SAR from ProfitMargins
        "room_type_pricing": room_pricing,
    }).insert(ignore_permissions=True)
    print("  → Hotel Pricing Config created (safety=3%, lock=90%)")


def _seed_factor_tables():
    from hotels_wave.hotels_wave.setup.seed_data import create_seed_data
    create_seed_data()
    print("  → Factor tables seeded")


def _create_hotel_reservations():
    existing_count = frappe.db.count("Hotel Reservation", {"hotel": HOTEL_CUSTOMER_NAME})
    if existing_count:
        print(f"  → Hotel Reservations: {existing_count} already exist — skipping")
        return

    created = 0
    for ut, status, ci_status, source, rental, check_in, check_out, rooms in HOTEL_RESERVATIONS:
        frappe.get_doc({
            "doctype": "Hotel Reservation",
            "hotel": HOTEL_CUSTOMER_NAME,
            "unit_type": ut,
            "status": status,
            "check_in_status": ci_status,
            "booking_source": source,
            "rental_type": rental,
            "check_in": check_in,
            "check_out": check_out,
            "number_of_rooms": rooms,
        }).insert(ignore_permissions=True)
        created += 1

    print(f"  → Hotel Reservations: {created} created")


def _create_booking_intake():
    """
    Create one confirmed Booking Intake: 100 rooms of غرفة ثنائية
    for Feb 1 → Mar 1, 2026, representing the Booked=100 in the Excel DailyCalendar.
    """
    existing = frappe.db.count("Booking Intake", {"hotel": HOTEL_CUSTOMER_NAME, "booking_status": "Confirmed"})
    if existing:
        print(f"  → Booking Intake: {existing} confirmed already exist — skipping")
        return

    ota = frappe.db.get_value("OTA Account Setup", {"hotel": HOTEL_CUSTOMER_NAME}, "name")
    if not ota:
        print("  ⚠  No OTA Account found — skipping Booking Intake creation")
        return

    doc = frappe.get_doc({
        "doctype": "Booking Intake",
        "hotel": HOTEL_CUSTOMER_NAME,
        "ota_source": ota,
        "check_in": "2026-02-01",
        "check_out": "2026-03-01",
        "booking_status": "Confirmed",
        "total_value": 0,
        "availability_control": [{
            "doctype": "Availability Control",
            "unit_type": "غرفة ثنائية",
            "allocated_units": 100,
        }],
    })
    doc.insert(ignore_permissions=True)

    # Skip on_booking_confirmed counter update — we'll use date-based queries
    print(f"  → Booking Intake created: {doc.name} (100 rooms غرفة ثنائية, Feb 1→Mar 1, Confirmed)")


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def _delete_test_data():
    for doctype, filters in [
        ("Hotel Reservation", {"hotel": HOTEL_CUSTOMER_NAME}),
        ("Booking Intake", {"hotel": HOTEL_CUSTOMER_NAME}),
        ("Hotel Pricing Config", {"hotel": HOTEL_CUSTOMER_NAME}),
        ("Hotel Cost Structure", {"hotel": HOTEL_CUSTOMER_NAME}),
        ("Hotel Season", {"hotel": HOTEL_CUSTOMER_NAME}),
        ("Hotel Unit Type", {"hotel": HOTEL_CUSTOMER_NAME}),
        ("OTA Account Setup", {"hotel": HOTEL_CUSTOMER_NAME}),
    ]:
        for name in frappe.get_all(doctype, filters=filters, pluck="name"):
            frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
            print(f"  Deleted {doctype}: {name}")

    for dt in ["Demand Pressure Factor"]:
        for name in frappe.get_all(dt, pluck="name"):
            frappe.delete_doc(dt, name, ignore_permissions=True, force=True)

    print("  → Test data deleted")
