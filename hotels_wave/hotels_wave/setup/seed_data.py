# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

"""
Seed data for Dynamic Pricing factor tables.
Values are taken DIRECTLY from the Excel file:
  نموذج التسعير الفندقي المتقدم.xlsx

Run with:
    bench execute hotels_wave.hotels_wave.setup.seed_data.create_seed_data

To update existing records (delete and re-insert):
    bench execute hotels_wave.hotels_wave.setup.seed_data.refresh_seed_data
"""

import frappe


def create_seed_data():
    """Insert all factor table seed records. Safe to re-run (skips duplicates)."""
    _seed_occupancy_yield_factors()
    _seed_day_of_week_factors()
    _seed_lead_time_factors()
    _seed_customer_segment_factors()
    _seed_length_of_stay_factors()
    _seed_rooms_volume_factors()
    _seed_booking_volume_discounts()
    _seed_pricing_plans()
    frappe.db.commit()
    print("✅  Seed data created successfully for all Dynamic Pricing factor tables.")


def refresh_seed_data():
    """Delete all existing factor records and re-insert with Excel values."""
    for dt in [
        "Occupancy Yield Factor", "Day Of Week Factor", "Lead Time Factor",
        "Customer Segment Factor", "Length Of Stay Factor",
        "Rooms Volume Factor", "Booking Volume Discount", "Pricing Plan",
    ]:
        for name in frappe.get_all(dt, pluck="name"):
            frappe.delete_doc(dt, name, ignore_permissions=True, force=True)
    frappe.db.commit()
    create_seed_data()


# ---------------------------------------------------------------------------
# 1. Occupancy Yield Factor
#    Source: OccupancyAndYield sheet
#    As occupancy rises, the price multiplier increases (yield management).
# ---------------------------------------------------------------------------
def _seed_occupancy_yield_factors():
    rows = [
        #  min%  max%   factor   description
        (  0,   50,   0.90,  "0-50% — Low demand, discount to fill rooms"),
        ( 50,   60,   0.95,  "50-60% — Below average demand"),
        ( 60,   70,   1.00,  "60-70% — Normal pricing (baseline)"),
        ( 70,   80,   1.05,  "70-80% — Moderate demand uplift"),
        ( 80,   90,   1.10,  "80-90% — High demand uplift"),
        ( 90,  100,   1.20,  "90-100% — Peak demand, maximum yield"),
    ]
    for min_occ, max_occ, factor, desc in rows:
        _insert("Occupancy Yield Factor", {
            "doctype": "Occupancy Yield Factor",
            "min_occupancy_pct": min_occ,
            "max_occupancy_pct": max_occ,
            "factor": factor,
            "description": desc,
        })
    print("  → Occupancy Yield Factor: {} rows".format(len(rows)))


# ---------------------------------------------------------------------------
# 2. Day Of Week Factor
#    Source: DayOfWeekFactors sheet
#    Thu/Fri are weekend peaks in Gulf region (Saudi Arabia).
# ---------------------------------------------------------------------------
def _seed_day_of_week_factors():
    rows = [
        # day,         factor  is_weekend
        ("Monday",     1.00,   0),
        ("Tuesday",    1.00,   0),
        ("Wednesday",  1.00,   0),
        ("Thursday",   1.10,   1),   # Gulf weekend starts Thu
        ("Friday",     1.10,   1),   # Gulf weekend peak
        ("Saturday",   1.00,   0),
        ("Sunday",     1.00,   0),
    ]
    for day, factor, is_wknd in rows:
        _insert("Day Of Week Factor", {
            "doctype": "Day Of Week Factor",
            "day_of_week": day,
            "factor": factor,
            "is_weekend": is_wknd,
        })
    print("  → Day Of Week Factor: {} rows".format(len(rows)))


# ---------------------------------------------------------------------------
# 3. Lead Time Factor
#    Source: LeadTimeFactors sheet
#    Measures days between booking date and check-in date (NOT today).
#    Last-minute bookings get a small premium; far-advance get a discount.
# ---------------------------------------------------------------------------
def _seed_lead_time_factors():
    rows = [
        # min_days  max_days  factor  description
        (  0,    1,  1.10,  "0-1 days — Same/next-day, slight scarcity premium"),
        (  2,    3,  1.08,  "2-3 days ahead"),
        (  4,    7,  1.05,  "4-7 days ahead"),
        (  8,   14,  1.02,  "8-14 days ahead"),
        ( 15,   30,  1.00,  "15-30 days — Standard rate (baseline)"),
        ( 31,   60,  0.97,  "31-60 days — Early booking discount"),
        ( 61,   90,  0.95,  "61-90 days — Advance discount"),
    ]
    for min_d, max_d, factor, desc in rows:
        _insert("Lead Time Factor", {
            "doctype": "Lead Time Factor",
            "min_days": min_d,
            "max_days": max_d,
            "factor": factor,
            "description": desc,
        })
    print("  → Lead Time Factor: {} rows".format(len(rows)))


# ---------------------------------------------------------------------------
# 4. Customer Segment Factor
#    Source: CustomerSegmentFactors sheet
#    Excel defines exactly 2 segments: B2C (retail) and B2B (corporate).
# ---------------------------------------------------------------------------
def _seed_customer_segment_factors():
    rows = [
        # segment  factor  (Excel sheet — exactly these 2 only)
        ("B2C",    1.00),   # Retail / direct — full price
        ("B2B",    0.85),   # Corporate — 15% negotiated discount
    ]
    for segment, factor in rows:
        _insert("Customer Segment Factor", {
            "doctype": "Customer Segment Factor",
            "segment": segment,
            "factor": factor,
        })
    print("  → Customer Segment Factor: {} rows".format(len(rows)))


# ---------------------------------------------------------------------------
# 5. Length Of Stay Factor
#    Source: LengthOfStayFactors sheet
#    Excel defines exactly 5 tiers (max is 15-30 nights).
#    Longer stays get progressively bigger discounts.
# ---------------------------------------------------------------------------
def _seed_length_of_stay_factors():
    rows = [
        # min  max   factor  description
        (  1,   1,  1.00,  "1 night — ليلة واحدة, no adjustment"),
        (  2,   3,  0.98,  "2-3 nights — إقامة قصيرة, short stay"),
        (  4,   6,  0.95,  "4-6 nights — إقامة متوسطة, medium stay"),
        (  7,  14,  0.90,  "7-14 nights — إقامة طويلة, weekly rate"),
        ( 15,  30,  0.85,  "15-30 nights — عروض شهرية, monthly offers"),
    ]
    for min_n, max_n, factor, desc in rows:
        _insert("Length Of Stay Factor", {
            "doctype": "Length Of Stay Factor",
            "min_nights": min_n,
            "max_nights": max_n,
            "factor": factor,
            "description": desc,
        })
    print("  → Length Of Stay Factor: {} rows".format(len(rows)))


# ---------------------------------------------------------------------------
# 6. Rooms Volume Factor
#    Measures this booking's rooms as a % of the hotel's total inventory.
#    Not in Excel — kept as extra guardrail for large block bookings.
# ---------------------------------------------------------------------------
def _seed_rooms_volume_factors():
    rows = [
        # min%   max%  factor
        (  0,   20,  0.95),   # 0-20% of inventory — small booking, slight discount
        ( 20,   40,  1.00),   # 20-40% — standard rate
        ( 40,   60,  1.03),   # 40-60% — moderate block premium
        ( 60,   80,  1.07),   # 60-80% — large block premium
        ( 80,  100,  2.00),   # 80-100% — near-buyout, maximum premium
    ]
    for min_p, max_p, factor in rows:
        _insert("Rooms Volume Factor", {
            "doctype": "Rooms Volume Factor",
            "min_pct": min_p,
            "max_pct": max_p,
            "factor": factor,
        })
    print("  → Rooms Volume Factor: {} rows".format(len(rows)))


# ---------------------------------------------------------------------------
# 7. Booking Volume Discount
#    Source: BookingRoomsDiscount sheet
#    Direct discount % applied after the main factor formula.
# ---------------------------------------------------------------------------
def _seed_booking_volume_discounts():
    rows = [
        # min_rooms  max_rooms  discount_pct
        (1,    1,   0),    # 1 room — no discount
        (2,    2,   3),    # 2 rooms — 3%
        (3,    3,   5),    # 3 rooms — 5%
        (4,    4,   7),    # 4 rooms — 7%
        (5,  999,  10),    # 5+ rooms — 10%
    ]
    for min_r, max_r, disc in rows:
        _insert("Booking Volume Discount", {
            "doctype": "Booking Volume Discount",
            "min_rooms": min_r,
            "max_rooms": max_r,
            "discount_pct": disc,
        })
    print("  → Booking Volume Discount: {} rows".format(len(rows)))


# ---------------------------------------------------------------------------
# 8. Pricing Plans
#    Source: PricingPlans sheet
# ---------------------------------------------------------------------------
def _seed_pricing_plans():
    rows = [
        # name               disc%  refund  min_stay  notes
        ("Standard Rate",     0,    1,      1,  "Full price, flexible cancellation"),
        ("Non-Refundable",   10,    0,      1,  "Cheapest option, no refund"),
        ("Corporate Rate",   15,    1,      2,  "For contracted B2B partners"),
        ("Promo Deal",       20,    0,      3,  "Limited-time offer for marketing campaigns"),
    ]
    for name, disc, refund, min_stay, desc in rows:
        _insert("Pricing Plan", {
            "doctype": "Pricing Plan",
            "plan_name": name,
            "discount_pct": disc,
            "is_refundable": refund,
            "min_stay_nights": min_stay,
            "description": desc,
        })
    print("  → Pricing Plan: {} rows".format(len(rows)))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _insert(doctype, data):
    """Insert a record, silently skip if it already exists."""
    try:
        doc = frappe.get_doc(data)
        doc.insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        pass
    except Exception as e:
        print(f"  ⚠  Could not insert {doctype} record: {e}")
