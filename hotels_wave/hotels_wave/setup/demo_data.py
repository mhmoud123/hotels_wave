# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

"""
Complete demo data for Hotels Wave — built EXACTLY from the Excel model:
  نموذج التسعير الفندقي المتقدم.xlsx

Hotel specs from RoomTypes sheet:
  Double  150 rooms  50% markup
  Triple  100 rooms  60% markup
  Quad    100 rooms  70% markup
  Suite   100 rooms  80% markup
  Total:  450 rooms

OTA channels from ChannelsAndCommissions sheet:
  Booking.com   15% commission  5% discount   no-show 20%/10%
  Expedia       18% commission  0% discount   no-show 22%/12%
  Hotel Website  0% commission  0% discount   no-show  8%/5%
  WhatsApp       0% commission  0% discount   no-show 10%/6%

Seasons from Seasonality sheet:
  Umrah              Jan 1  – Feb 17   ×1.3
  Ramadan 1st 10d    Feb 17 – Feb 27   ×2.0
  Ramadan 2nd 10d    Feb 27 – Mar 9    ×2.2
  Ramadan 3rd 10d    Mar 9  – Mar 19   ×4.0   (peak!)
  Eid Al-Fitr        Mar 19 – Mar 25   ×1.3

Financial targets from ProfitMargins sheet:
  Monthly profit target : 100,000 SAR
  Min profit per night  :     10  SAR
  Min margin            :     25  %
  Lock threshold        :     92  %

Run AFTER bench migrate and seed_data:
    bench execute hotels_wave.hotels_wave.setup.demo_data.create_demo_data

To wipe and recreate:
    bench execute hotels_wave.hotels_wave.setup.demo_data.drop_demo_data
    bench execute hotels_wave.hotels_wave.setup.demo_data.create_demo_data
"""

import frappe
from frappe.utils import today, add_days, getdate

# ---------------------------------------------------------------------------
# Constants — direct from Excel
# ---------------------------------------------------------------------------
HOTEL_NAME = "Grand Palace Hotel"
CURRENCY   = "SAR"

# RoomTypes sheet: (type_name, total_units, allowed_units, max_occupancy)
# Pricing lives in Hotel Pricing Config, NOT here.
UNIT_TYPES = [
    ("Double Room",  150, 140, 2),
    ("Triple Room",  100,  95, 3),
    ("Quad Room",    100,  95, 4),
    ("Suite",        100,  95, 2),
]
# Total: 450 rooms (matches Excel)

# Markup % per room type — only editable field in Hotel Pricing Config room_type_pricing.
# Suggested Base Price = cost_per_night (from cost structure) × (1 + markup%)
# Markup % matches Excel RoomTypes sheet exactly: 50/60/70/80
UNIT_TYPE_MARKUP = {
    "Double Room": 50,
    "Triple Room": 60,
    "Quad Room":   70,
    "Suite":       80,
}

# ChannelsAndCommissions sheet:
# (item_code, commission_pct, channel_discount_pct, channel_type, no_show_weekday_pct, no_show_weekend_pct)
OTA_CHANNELS = [
    ("Booking.com",    15, 5, "OTA",    20, 10),
    ("Expedia",        18, 0, "OTA",    22, 12),
    ("Hotel Website",   0, 0, "Direct",  8,  5),
    ("WhatsApp",        0, 0, "Direct", 10,  6),
]

# Seasonality sheet — 2026 Islamic calendar dates (approximate Hijri to Gregorian)
# Each tuple: (season_type, label, start_date, end_date, factor, unit_prices)
# Unit prices = base_price × factor for each room type
SEASONS_2026 = [
    # Umrah season ×1.3
    ("Mid", "Umrah Season 2026",
     "2026-01-01", "2026-02-17", 1.3,
     {"Double Room": 260, "Triple Room": 364, "Quad Room": 455, "Suite": 975}),

    # Ramadan 1st 10 days ×2.0
    ("High", "Ramadan 1st 10 Days 2026",
     "2026-02-18", "2026-02-27", 2.0,
     {"Double Room": 400, "Triple Room": 560, "Quad Room": 700, "Suite": 1500}),

    # Ramadan 2nd 10 days ×2.2
    ("High", "Ramadan 2nd 10 Days 2026",
     "2026-02-28", "2026-03-09", 2.2,
     {"Double Room": 440, "Triple Room": 616, "Quad Room": 770, "Suite": 1650}),

    # Ramadan 3rd 10 days ×4.0  ← THE BIG ONE
    ("High", "Ramadan 3rd 10 Days 2026",
     "2026-03-10", "2026-03-19", 4.0,
     {"Double Room": 800, "Triple Room": 1120, "Quad Room": 1400, "Suite": 3000}),

    # Eid Al-Fitr ×1.3
    ("Mid", "Eid Al-Fitr 2026",
     "2026-03-20", "2026-03-25", 1.3,
     {"Double Room": 260, "Triple Room": 364, "Quad Room": 455, "Suite": 975}),
]

SEASONS_2027 = [
    # Umrah season ×1.3
    ("Mid", "Umrah Season 2027",
     "2027-01-01", "2027-02-06", 1.3,
     {"Double Room": 260, "Triple Room": 364, "Quad Room": 455, "Suite": 975}),

    # Ramadan 2027 1st 10 days ×2.0
    ("High", "Ramadan 1st 10 Days 2027",
     "2027-02-07", "2027-02-16", 2.0,
     {"Double Room": 400, "Triple Room": 560, "Quad Room": 700, "Suite": 1500}),

    # Ramadan 2027 2nd 10 days ×2.2
    ("High", "Ramadan 2nd 10 Days 2027",
     "2027-02-17", "2027-02-26", 2.2,
     {"Double Room": 440, "Triple Room": 616, "Quad Room": 770, "Suite": 1650}),

    # Ramadan 2027 3rd 10 days ×4.0
    ("High", "Ramadan 3rd 10 Days 2027",
     "2027-02-27", "2027-03-08", 4.0,
     {"Double Room": 800, "Triple Room": 1120, "Quad Room": 1400, "Suite": 3000}),

    # Eid Al-Fitr 2027 ×1.3
    ("Mid", "Eid Al-Fitr 2027",
     "2027-03-09", "2027-03-15", 1.3,
     {"Double Room": 260, "Triple Room": 364, "Quad Room": 455, "Suite": 975}),
]

ALL_SEASONS = SEASONS_2026 + SEASONS_2027

# Fixed Costs (FixedAndVariableCosts sheet) — 83,500 SAR/month total
# breakdown: Labor, Reception, Management, Accounting, Security, etc.
FIXED_COSTS = [
    # (category, description, monthly_SAR)
    ("Staff",       "Housekeeping & Labor",         45000),
    ("Staff",       "Reception staff",              12000),
    ("Staff",       "Management salaries",          15000),
    ("Staff",       "Accounting department",         5500),
    ("Staff",    "Security & guarding",           6000),
]
# Total: 83,500 SAR/month ✓

# Variable Costs per room per night (from FixedAndVariableCosts sheet)
# Hospitality: Double 4.8 SR, Triple 7.0 SR, Quad 8.5 SR, Suite 10.0 SR
# Laundry: 12.4 SR/room/night (all types)
# Utilities: 13.0 SR/room/night (all types)
#
# IMPORTANT: For Variable cost items the HotelCostStructure controller stores
# monthly_amount directly as cost_per_room_per_night (no division).
# Therefore these MUST be the per-room-per-night rates from the Excel, NOT monthly totals.
VARIABLE_COSTS = [
    # (category, description, unit_type, per_room_per_night_SAR)
    ("Supplies",    "Guest hospitality - Double",      "Double Room",   4.8),
    ("Supplies",    "Guest hospitality - Triple",      "Triple Room",   7.0),
    ("Supplies",    "Guest hospitality - Quad",        "Quad Room",     8.5),
    ("Supplies",    "Guest hospitality - Suite",       "Suite",        10.0),
    ("Supplies",    "Laundry & linen service",         None,           12.4),
    ("Utilities",   "Electricity, water & utilities",  None,           13.0),
]

# Demo Bookings — designed to showcase dynamic pricing and overbooking
# Offsets are from today() (2026-02-23).
# Check-in dates landing in Ramadan periods show the ×4.0 factor effect.
#
# (unit_type, check_in_offset, nights, ota_code, segment, plan, units, total_value_SAR)
BOOKINGS = [
    # --- Ramadan 2nd period (around Feb 27+, factor ×2.2) ---
    # 4 days from now = Feb 27 (Ramadan 2nd starts, factor 2.2)
    ("Double Room",  4,  4, "Booking.com",   "B2C", "Standard Rate",   3,  5280),
    ("Triple Room",  5,  3, "Expedia",        "B2C", "Non-Refundable",  2,  3695),
    ("Double Room",  6,  5, "Hotel Website",  "B2B", "Corporate Rate",  5, 11000),

    # --- Ramadan 3rd period (Mar 9+, PEAK factor ×4.0) ---
    # 14 days from now = Mar 9 (Ramadan 3rd starts)
    ("Double Room", 14,  3, "Booking.com",   "B2C", "Standard Rate",   4, 10752),
    ("Suite",       14,  2, "Hotel Website", "B2C", "Standard Rate",   1,  6000),
    ("Double Room", 16,  4, "Expedia",        "B2C", "Non-Refundable",  6, 19353),
    ("Triple Room", 17,  3, "WhatsApp",       "B2B", "Corporate Rate",  3,  8568),
    ("Quad Room",   15,  5, "Hotel Website",  "B2B", "Corporate Rate",  4, 23800),
    ("Suite",       18,  3, "Booking.com",   "B2C", "Standard Rate",   2, 17136),

    # --- Eid Al-Fitr period (Mar 19+, factor ×1.3) ---
    # 24 days from now = Mar 19 (Eid starts)
    ("Double Room", 24,  4, "Hotel Website", "B2C", "Standard Rate",   5,  5200),
    ("Triple Room", 25,  3, "WhatsApp",      "B2C", "Standard Rate",   2,  2184),
    ("Quad Room",   26,  2, "Expedia",        "B2B", "Corporate Rate",  3,  2940),

    # --- Normal season (post-Eid, factor ×1.0) ---
    # 30+ days from now = late March / April, normal pricing
    ("Double Room", 32,  7, "Hotel Website",  "B2B", "Corporate Rate",  8,  9520),
    ("Suite",       35,  5, "Booking.com",   "B2C", "Promo Deal",       1,  3000),

    # --- Open (un-confirmed) bookings to show MEDIUM/HIGH overbooking risk ---
    ("Double Room",  1,  1, "Booking.com",   "B2C", "Standard Rate",    1,   240),
    ("Double Room", 14,  4, "WhatsApp",      "B2C", "Standard Rate",   20, 64000),  # large block → HIGH risk
]


# ===========================================================================
# MAIN ENTRY POINT
# ===========================================================================

def create_demo_data():
    print("\n🏨  Creating demo data for Grand Palace Hotel …\n")
    print("    Source: نموذج التسعير الفندقي المتقدم.xlsx\n")

    _create_unit_types()
    hotel = _create_hotel_customer()
    _create_hotel_unit_type(hotel)
    _create_ota_items_and_accounts(hotel)
    _create_hotel_seasons(hotel)
    # Cost structure MUST be created before pricing config so that
    # Hotel Pricing Config.validate() can read cost_per_night to compute suggested_price.
    _create_hotel_cost_structure(hotel)
    _create_hotel_pricing_config(hotel)
    _create_bookings(hotel)

    frappe.db.commit()
    print("\n✅  Demo data creation complete.")
    print(f"    Hotel     : {hotel}")
    print(f"    Rooms     : 450 (Double 150 + Triple 100 + Quad 100 + Suite 100)")
    print(f"    Site      : {frappe.local.site}")
    print("\n    ── Demo Navigation ──────────────────────────────────────────")
    print("    1. Hotels Wave → Dynamic Pricing Dashboard report")
    print("       Filter by hotel & date range 2026-03-09 to 2026-03-19")
    print("       → See Ramadan 3rd 10-day ×4.0 peak pricing in action")
    print("    2. Hotels Wave → Booking Intake → New")
    print("       Select Hotel Website / B2C / Double Room / check-in Mar 12")
    print("       → Click 'Calculate Price' to see ×4.0 season + occupancy yield")
    print("    3. Hotels Wave → Overbooking Calendar report")
    print("       → See HIGH risk flag on Double Room for Mar 9-19 (large block)")
    print("    4. Hotels Wave → Booking Intake list → open any confirmed booking")
    print("       → Submit → Financial Settlement auto-created")
    print("    ─────────────────────────────────────────────────────────────\n")


def drop_demo_data():
    """Delete all demo records so create_demo_data() can be re-run cleanly."""
    print("🗑   Dropping demo data …")
    _safe_delete("Booking Intake",       {"hotel": HOTEL_NAME})
    _safe_delete("Hotel Cost Structure", {"hotel": HOTEL_NAME})
    _safe_delete("Hotel Pricing Config", {"hotel": HOTEL_NAME})
    _safe_delete("Hotel Season",         {"hotel": HOTEL_NAME})
    _safe_delete("OTA Account Setup",    {"hotel": HOTEL_NAME})
    _safe_delete("Hotel Unit Type",      {"hotel": HOTEL_NAME})
    for ut, *_ in UNIT_TYPES:
        _safe_delete("Unit Type", {"type_name": ut})
    for ota, *_ in OTA_CHANNELS:
        _safe_delete("Item", {"item_code": ota})
    if frappe.db.exists("Customer", HOTEL_NAME):
        frappe.delete_doc("Customer", HOTEL_NAME, ignore_permissions=True, force=True)
    frappe.db.commit()
    print("✅  Demo data dropped.\n")


# ===========================================================================
# STEP 1 — Unit Types (RoomTypes sheet)
# ===========================================================================

def _create_unit_types():
    created = 0
    for ut, *_ in UNIT_TYPES:
        if not frappe.db.exists("Unit Type", ut):
            frappe.get_doc({"doctype": "Unit Type", "type_name": ut}).insert(ignore_permissions=True)
            created += 1
    print(f"  [1/8] Unit Types        : {created} created  (Double/Triple/Quad/Suite — 450 rooms total, no prices here)")


# ===========================================================================
# STEP 2 — Hotel Customer
# ===========================================================================

def _create_hotel_customer():
    if frappe.db.exists("Customer", HOTEL_NAME):
        print(f"  [2/8] Hotel Customer    : already exists ({HOTEL_NAME})")
        return HOTEL_NAME

    cust = frappe.get_doc({
        "doctype":               "Customer",
        "customer_name":         HOTEL_NAME,
        "customer_type":         "Company",
        "customer_group":        _get_or_default("Customer Group", "Commercial", "All Customer Groups"),
        "territory":             _get_or_default("Territory", "Saudi Arabia", "All Territories"),
        "custom_is_hotel_entity": 1,
        "custom_hotel_name":     HOTEL_NAME,
        "custom_hotel_status":   "Contracted",
        "custom_hotel_type":     "Hotel Apartments",
        "custom_city":           "Riyadh",
    })
    cust.insert(ignore_permissions=True)
    print(f"  [2/8] Hotel Customer    : created → {HOTEL_NAME}")
    return HOTEL_NAME


# ===========================================================================
# STEP 3 — Hotel Unit Type + Hotel Unit Detail rows
#           RoomTypes sheet: Double(150), Triple(100), Quad(100), Suite(100)
# ===========================================================================

def _create_hotel_unit_type(hotel):
    doc_name = f"{hotel}-Units"
    if frappe.db.exists("Hotel Unit Type", doc_name):
        print(f"  [3/8] Hotel Unit Type   : already exists ({doc_name})")
        return

    units_list = []
    for ut, total, allowed, max_occ in UNIT_TYPES:
        units_list.append({
            "doctype":                    "Hotel Unit Detail",
            "unit_type_ref":              ut,
            "total_units":                total,
            "units_allowed_on_platforms": allowed,
            "overbooked":                 0,
            "max_occupancy":              max_occ,
        })

    frappe.get_doc({
        "doctype":    "Hotel Unit Type",
        "hotel":      hotel,
        "units_list": units_list,
    }).insert(ignore_permissions=True)
    print(f"  [3/8] Hotel Unit Type   : created → {doc_name} (450 rooms across 4 types)")


# ===========================================================================
# STEP 4 — OTA Items + OTA Account Setup
#           ChannelsAndCommissions sheet
# ===========================================================================

def _create_ota_items_and_accounts(hotel):
    item_group = _get_or_default("Item Group", "Services", "All Item Groups")
    created_items = 0
    created_accounts = 0

    for ota_code, commission, ch_discount, ch_type, wkday_ns, wkend_ns in OTA_CHANNELS:
        # Item
        if not frappe.db.exists("Item", ota_code):
            frappe.get_doc({
                "doctype":         "Item",
                "item_code":       ota_code,
                "item_name":       ota_code,
                "item_group":      item_group,
                "is_stock_item":   0,
                "is_service_item": 1,
            }).insert(ignore_permissions=True)
            created_items += 1

        # OTA Account Setup
        ota_doc_name = f"{hotel}-{ota_code}"
        if not frappe.db.exists("OTA Account Setup", ota_doc_name):
            frappe.get_doc({
                "doctype":              "OTA Account Setup",
                "hotel":                hotel,
                "ota_name":             ota_code,
                "connection_type":      "Manual",
                "platform_commission":  commission,
                "channel_discount_pct": ch_discount,
                "channel_type":         ch_type,
                "no_show_rate_weekday": wkday_ns,
                "no_show_rate_weekend": wkend_ns,
            }).insert(ignore_permissions=True)
            created_accounts += 1

    print(f"  [4/8] OTA Accounts      : {created_items} items + {created_accounts} account setups")
    print("        Booking.com(15%/20%wk) Expedia(18%/22%wk) Website(0%/8%wk) WhatsApp(0%/10%wk)")


# ===========================================================================
# STEP 5 — Hotel Seasons (Seasonality sheet)
#           Umrah × Ramadan 3-phases × Eid — for 2026 and 2027
# ===========================================================================

def _create_hotel_seasons(hotel):
    created = 0
    for season_type, name_label, start, end, factor, prices in ALL_SEASONS:
        doc_name = f"{hotel}-{name_label}"
        if frappe.db.exists("Hotel Season", doc_name):
            continue

        season_unit_rates = [
            {
                "doctype":   "Season Unit Rates",
                "unit_type": ut,
                "price":     price,
                "currency":  CURRENCY,
            }
            for ut, price in prices.items()
        ]

        frappe.get_doc({
            "doctype":           "Hotel Season",
            "hotel":             hotel,
            "season_type":       season_type,
            "season_name_label": name_label,
            "start_date":        start,
            "end_date":          end,
            "season_factor":     factor,
            "season_unit_rates": season_unit_rates,
        }).insert(ignore_permissions=True)
        created += 1

    print(f"  [5/8] Hotel Seasons     : {created} seasons created (Umrah + Ramadan 3-phases + Eid × 2 years)")
    print("        Factors: ×1.3 / ×2.0 / ×2.2 / ×4.0 / ×1.3 (from Seasonality sheet)")


# ===========================================================================
# STEP 6 — Hotel Pricing Config (ProfitMargins + FactorWeights sheets)
# ===========================================================================

def _create_hotel_pricing_config(hotel):
    config_name = f"{hotel}-Pricing"
    if frappe.db.exists("Hotel Pricing Config", config_name):
        print(f"  [6/8] Pricing Config    : already exists ({config_name})")
        return

    # Only markup_pct is set here.
    # cost_per_night and suggested_price are auto-computed during validate()
    # from the Hotel Cost Structure that was created in the previous step.
    room_type_pricing = [
        {
            "doctype":    "Hotel Room Type Pricing",
            "unit_type":  ut,
            "markup_pct": UNIT_TYPE_MARKUP[ut],
            "currency":   CURRENCY,
        }
        for ut, *_ in UNIT_TYPES
    ]

    frappe.get_doc({
        "doctype":               "Hotel Pricing Config",
        "hotel":                 hotel,
        "is_active":             1,
        # ProfitMargins sheet — exact Excel values
        "target_monthly_profit": 100000,   # 100,000 SAR/month
        "min_profit_per_night":  10,       # 10 SAR minimum
        "min_margin_pct":        25,       # 25% minimum margin
        # FactorWeights sheet — exact Excel values
        "w_occupancy":           1.2,      # OccupancyAndYield weight
        "w_seasonality":         1.1,      # Seasonality weight
        "w_day_of_week":         1.0,
        "w_lead_time":           1.0,
        "w_customer_segment":    1.0,
        "w_length_of_stay":      1.0,
        "w_rooms_volume":        1.0,
        # OverbookingControl sheet
        "lock_threshold_pct":    92,       # lock when AdjOcc >= 92%
        "safety_buffer_rate":    5,        # 5% safety buffer
        # Room type pricing
        "room_type_pricing":     room_type_pricing,
    }).insert(ignore_permissions=True)
    print(f"  [6/8] Pricing Config    : created → markup set, suggested prices auto-computed from costs")


# ===========================================================================
# STEP 7 — Hotel Cost Structure (FixedAndVariableCosts sheet)
#           Fixed = 83,500 SAR/month, Variable per room-night from Excel
# ===========================================================================

def _create_hotel_cost_structure(hotel):
    cost_name = f"{hotel}-Costs"
    if frappe.db.exists("Hotel Cost Structure", cost_name):
        print(f"  [7/8] Cost Structure    : already exists ({cost_name})")
        return

    cost_items = []

    # Fixed costs — exact breakdown summing to 83,500 SAR/month
    for cat, desc, amount in FIXED_COSTS:
        cost_items.append({
            "doctype":        "Hotel Cost Item",
            "cost_category":  cat,
            "description":    desc,
            "unit_type":      None,
            "cost_type":      "Fixed",
            "monthly_amount": amount,
            "currency":       CURRENCY,
        })

    # Variable costs — per Excel rates × room count × 30 days (full occupancy reference)
    for cat, desc, ut, amount in VARIABLE_COSTS:
        cost_items.append({
            "doctype":        "Hotel Cost Item",
            "cost_category":  cat,
            "description":    desc,
            "unit_type":      ut,
            "cost_type":      "Variable",
            "monthly_amount": amount,
            "currency":       CURRENCY,
        })

    frappe.get_doc({
        "doctype":        "Hotel Cost Structure",
        "hotel":          hotel,
        "effective_date": today(),
        "cost_items":     cost_items,
    }).insert(ignore_permissions=True)
    fixed_total = sum(a for _, _, a in FIXED_COSTS)
    print(f"  [7/8] Cost Structure    : created → {len(cost_items)} lines (fixed {fixed_total:,} SAR + variable)")


# ===========================================================================
# STEP 8 — Booking Intakes
#           Spans Ramadan 2nd → 3rd peak → Eid → Normal seasons
#           Shows dynamic price multipliers in action (×2.2 → ×4.0 → ×1.3 → ×1.0)
# ===========================================================================

def _create_bookings(hotel):
    created   = 0
    confirmed = 0

    for i, (unit_type, ci_offset, nights, ota_code, segment, plan, units, value) in enumerate(BOOKINGS):
        ota_doc = f"{hotel}-{ota_code}"
        if not frappe.db.exists("OTA Account Setup", ota_doc):
            print(f"  ⚠  OTA account not found: {ota_doc}, skipping booking {i+1}")
            continue

        check_in  = add_days(today(), ci_offset)
        check_out = add_days(check_in, nights)

        booking = frappe.get_doc({
            "doctype":          "Booking Intake",
            "hotel":            hotel,
            "ota_source":       ota_doc,
            "check_in":         check_in,
            "check_out":        check_out,
            "currency":         CURRENCY,
            "total_value":      value,
            "booking_status":   "Open",
            "unit_type":        unit_type,
            "customer_segment": segment,
            "pricing_plan":     plan,
            "guest_name":       f"Demo Guest {i + 1}",
            "phone_number":     f"+9665{50000000 + i}",
            "availability_control": [{
                "doctype":         "Availability Control",
                "unit_type":       unit_type,
                "allocated_units": units,
            }],
        })
        booking.insert(ignore_permissions=True)
        created += 1

        # Confirm all but the last 2 (leave as Open to show HIGH/MEDIUM risk)
        if i < len(BOOKINGS) - 2:
            booking.booking_status = "Confirmed"
            booking.submit()
            confirmed += 1

    print(f"\n  [8/8] Bookings          : {created} created, {confirmed} confirmed")
    print("        (Last 2 left as 'Open' to show MEDIUM/HIGH overbooking risk on Dashboard)")
    print("        Booking dates span: Ramadan 2nd (×2.2) → 3rd Peak (×4.0) → Eid (×1.3) → Normal (×1.0)")


# ===========================================================================
# Utilities
# ===========================================================================

def _get_or_default(doctype, preferred, fallback):
    if frappe.db.exists(doctype, preferred):
        return preferred
    rows = frappe.get_all(doctype, limit=1, pluck="name")
    return rows[0] if rows else fallback


def _safe_delete(doctype, filters):
    names = frappe.get_all(doctype, filters=filters, pluck="name")
    for name in names:
        try:
            doc = frappe.get_doc(doctype, name)
            if getattr(doc, "docstatus", 0) == 1:
                doc.cancel()
            frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
        except Exception as e:
            print(f"  ⚠  Could not delete {doctype} '{name}': {e}")
