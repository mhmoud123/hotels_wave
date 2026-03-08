# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

"""
Overbooking Engine for Hotels Wave.

Calculates sellable rooms, adjusted occupancy, lock status, and risk level
for a given hotel / unit-type / date / channel combination.

DailyCalendar Formula (from Excel):
    Booked              = OTA/advance rooms overlapping the date (from Booking Intake)
    In-House + Arrivals = all guests physically present (from Hotel Reservation)
    Arrivals            = OTA-source guests arriving on exactly this date (from Hotel Reservation)
    Expected Occupied   = InHouse + MAX(0, Booked - Arrivals) × (1 - NoShow%)
    Sellable            = Physical + MAX_Overbook - SafetyBuffer
    Adj Occ % (display) = Expected Occupied / Physical Rooms
    Exp Occ (pricing)   = Expected Occupied / Sellable Rooms
"""

import math
from datetime import date, timedelta

import frappe
from frappe.utils import getdate


def _excel_round(x):
    """Round like Excel ROUND() — .5 always rounds UP (vs Python banker's rounding)."""
    return math.floor(x + 0.5)


# OTA sources that can no-show (for Arrivals filtering)
OTA_SOURCES = [
    "Booking", "Expedia", "booking", "booking.com",
    "بوكينج", "بوكنج", "بوكينغ", "بوكنغ",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_overbooking_status(hotel, unit_type, check_in, ota_source=None):
    """
    Return a dict with full overbooking/occupancy analysis for a date:
        physical_rooms, max_overbook, safety_buffer, sellable_rooms,
        booked_rooms, in_house_arrivals, arrivals, expected_occupied,
        adj_occupancy_pct, exp_occ_for_pricing, lock_status, risk_level
    """
    check_in = getdate(check_in)

    physical_rooms = _get_physical_rooms(hotel, unit_type)
    if not physical_rooms:
        return _empty_status()

    config = _get_config(hotel)
    safety_buffer_rate = (config.safety_buffer_rate or 5) / 100 if config else 0.05
    lock_threshold = (config.lock_threshold_pct or 92) / 100 if config else 0.92

    no_show_rate = _get_no_show_rate(ota_source, check_in) / 100

    max_overbook = _excel_round(physical_rooms * no_show_rate)
    safety_buffer = max(1, _excel_round(physical_rooms * safety_buffer_rate))
    sellable = max(1, physical_rooms + max_overbook - safety_buffer)

    # Date-based queries
    booked = get_booked_rooms_for_date(hotel, unit_type, check_in)
    in_house = get_in_house_and_arrivals(hotel, unit_type, check_in)
    arrivals = get_arrivals(hotel, unit_type, check_in)
    expected = get_expected_occupied(hotel, unit_type, check_in, ota_source)

    # If no Hotel Reservation records exist, fall back to static counters
    if not in_house and not arrivals:
        _, static_booked = _get_room_counts(hotel, unit_type)
        if static_booked:
            expected = static_booked
            booked = static_booked

    # Two occupancy calculations per Excel
    adj_occ_display = expected / physical_rooms if physical_rooms else 0
    exp_occ_pricing = expected / sellable if sellable else 0

    locked = adj_occ_display >= lock_threshold
    lock_status = "LOCK" if locked else "OPEN"

    if locked or expected > sellable:
        risk_level = "HIGH"
    elif adj_occ_display >= 0.8:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "physical_rooms": physical_rooms,
        "max_overbook": max_overbook,
        "safety_buffer": safety_buffer,
        "sellable_rooms": sellable,
        "booked_rooms": booked,
        "in_house_arrivals": in_house,
        "arrivals": arrivals,
        "expected_occupied": expected,
        "adj_occupancy_pct": round(adj_occ_display * 100, 2),
        "exp_occ_for_pricing": round(exp_occ_pricing, 4),
        "lock_status": lock_status,
        "risk_level": risk_level,
    }


def get_daily_calendar(hotel, unit_type, from_date, to_date, ota_source=None):
    """
    Return a list of dicts (one per day) for the overbooking calendar report.
    Pass ota_source so the correct no-show rate (channel-specific) is applied.
    """
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    results = []
    current = from_date
    while current <= to_date:
        status = get_overbooking_status(hotel, unit_type, current, ota_source)
        status["date"] = str(current)
        status["day_of_week"] = current.strftime("%A")
        results.append(status)
        current += timedelta(days=1)
    return results


def refresh_all_overbooking_statuses():
    """
    Daily scheduler job: logs overbooking risk for all active hotel/unit-type combos.
    Called from hooks.py scheduler_events.
    """
    hotels = frappe.get_all(
        "Hotel Pricing Config",
        filters={"is_active": 1},
        fields=["hotel"],
    )
    today = date.today()
    for h in hotels:
        hotel = h.hotel
        hotel_unit_type = frappe.db.get_value("Hotel Unit Type", {"hotel": hotel}, "name")
        if not hotel_unit_type:
            continue
        unit_types = frappe.get_all(
            "Hotel Unit Detail",
            filters={"parent": hotel_unit_type},
            pluck="unit_type_ref",
        )
        for unit_type in unit_types:
            status = get_overbooking_status(hotel, unit_type, today)
            if status.get("risk_level") == "HIGH":
                frappe.log_error(
                    message=str(status),
                    title=f"HIGH Overbooking Risk: {hotel} / {unit_type} / {today}",
                )


# ---------------------------------------------------------------------------
# Date-based query functions (DailyCalendar)
# ---------------------------------------------------------------------------

def get_booked_rooms_for_date(hotel, unit_type, target_date):
    """
    Query Booking Intake (confirmed) overlapping target_date.
    Returns total rooms from OTA/advance bookings.
    """
    target_date = getdate(target_date)
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(ac.allocated_units), 0) as total
        FROM `tabBooking Intake` bi
        JOIN `tabAvailability Control` ac ON ac.parent = bi.name
        WHERE bi.hotel = %s
          AND ac.unit_type = %s
          AND bi.booking_status = 'Confirmed'
          AND bi.check_in <= %s
          AND bi.check_out > %s
    """, (hotel, unit_type, target_date, target_date), as_dict=True)
    return int(result[0].total) if result else 0


def get_in_house_and_arrivals(hotel, unit_type, target_date):
    """
    Query Hotel Reservation (مؤكد status) overlapping target_date.
    Returns total rooms from ALL sources (Booking + استقبال + اخرى etc).
    """
    target_date = getdate(target_date)
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(number_of_rooms), 0) as total
        FROM `tabHotel Reservation`
        WHERE hotel = %s
          AND unit_type = %s
          AND status = 'مؤكد'
          AND check_in <= %s
          AND check_out > %s
    """, (hotel, unit_type, target_date, target_date), as_dict=True)
    return int(result[0].total) if result else 0


def get_arrivals(hotel, unit_type, target_date):
    """
    Query Hotel Reservation where check_in == target_date
    AND booking_source is OTA (Booking, Expedia, etc.)
    Returns rooms arriving today from OTA sources (can no-show).
    """
    target_date = getdate(target_date)
    if not OTA_SOURCES:
        return 0
    placeholders = ", ".join(["%s"] * len(OTA_SOURCES))
    result = frappe.db.sql(f"""
        SELECT COALESCE(SUM(number_of_rooms), 0) as total
        FROM `tabHotel Reservation`
        WHERE hotel = %s
          AND unit_type = %s
          AND status = 'مؤكد'
          AND check_in = %s
          AND booking_source IN ({placeholders})
    """, [hotel, unit_type, target_date] + OTA_SOURCES, as_dict=True)
    return int(result[0].total) if result else 0


def get_expected_occupied(hotel, unit_type, target_date, ota_source=None):
    """
    The core formula from the Excel DailyCalendar:

    Expected Occupied = InHouse + MAX(0, Booked - Arrivals) × (1 - NoShow%)
    """
    target_date = getdate(target_date)
    ih = get_in_house_and_arrivals(hotel, unit_type, target_date)
    ar = get_arrivals(hotel, unit_type, target_date)
    bk = get_booked_rooms_for_date(hotel, unit_type, target_date)
    ns = _get_no_show_rate(ota_source, target_date) / 100

    return ih + max(0, bk - ar) * (1 - ns)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_physical_rooms(hotel, unit_type):
    """Return total physical rooms for a hotel/unit_type."""
    hotel_unit_type = frappe.db.get_value("Hotel Unit Type", {"hotel": hotel}, "name")
    if not hotel_unit_type:
        return 0
    total = frappe.db.get_value(
        "Hotel Unit Detail",
        {"parent": hotel_unit_type, "unit_type_ref": unit_type},
        "total_units",
    )
    return int(total or 0)


def _get_room_counts(hotel, unit_type):
    """Return (total_physical_rooms, currently_booked) from static counters — fallback."""
    hotel_unit_type = frappe.db.get_value("Hotel Unit Type", {"hotel": hotel}, "name")
    if not hotel_unit_type:
        return 0, 0

    detail = frappe.db.get_value(
        "Hotel Unit Detail",
        {"parent": hotel_unit_type, "unit_type_ref": unit_type},
        ["total_units", "units_allowed_on_platforms", "overbooked"],
        as_dict=True,
    )
    if not detail:
        return 0, 0

    physical = detail.total_units or 0
    available = detail.units_allowed_on_platforms or 0
    overbooked = detail.overbooked or 0
    booked = (physical - available) + overbooked
    return physical, max(0, booked)


def _get_config(hotel):
    config_name = frappe.db.get_value(
        "Hotel Pricing Config", {"hotel": hotel, "is_active": 1}, "name"
    )
    if not config_name:
        return None
    return frappe.get_doc("Hotel Pricing Config", config_name)


def _get_no_show_rate(ota_source, check_in):
    """Return the applicable no-show rate % based on weekday/weekend."""
    if not ota_source:
        return 5.0  # default 5%

    ota = frappe.db.get_value(
        "OTA Account Setup",
        ota_source,
        ["no_show_rate_weekday", "no_show_rate_weekend"],
        as_dict=True,
    )
    if not ota:
        return 5.0

    # Weekend = Thursday and Friday in Middle East
    # Using ISO weekday: Mon=1 ... Sun=7; treat 4 (Thu) and 5 (Fri) as weekend
    is_weekend = getdate(check_in).isoweekday() in (4, 5)

    if is_weekend:
        return float(ota.no_show_rate_weekend or 5.0)
    return float(ota.no_show_rate_weekday or 5.0)


def _empty_status():
    return {
        "physical_rooms": 0,
        "max_overbook": 0,
        "safety_buffer": 0,
        "sellable_rooms": 0,
        "booked_rooms": 0,
        "in_house_arrivals": 0,
        "arrivals": 0,
        "expected_occupied": 0,
        "adj_occupancy_pct": 0,
        "exp_occ_for_pricing": 0,
        "lock_status": "OPEN",
        "risk_level": "LOW",
    }
