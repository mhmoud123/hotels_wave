# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

"""
Overbooking Engine for Hotels Wave.

Calculates sellable rooms, occupancy metrics, lock status, and risk level
for a given hotel / unit-type / date combination.

DailyCalendar Formula:
    Booked          = OTA/advance rooms arriving on the date (from Booking Intake)
    In-House        = guests checked in with check_in <= today < check_out (Hotel Reservation)
    Arrivals        = OTA-source guests arriving exactly today (Hotel Reservation)
    No-Show Rooms   = Physical Rooms × No-Show Rate %
    Sellable        = Physical Rooms + No-Show Rooms - Safety Buffer Rooms
    Expected Occ    = MAX(0, (Booked - Arrivals) × (1 - NoShow%)) + In-House
    Occupancy %     = Expected Occupied / Physical Rooms
    Real Occupancy  = In-House / Physical Rooms
    Exp Occ (pricing) = Expected Occupied / Sellable Rooms

No-Show Rate hierarchy:
    1. Hotel Season override (if date falls within a season with rate defined)
    2. Hotel (Customer) default rate
    3. System default: 5%
"""

import math
from datetime import date, timedelta

import frappe
from frappe.utils import getdate


def _excel_round(x):
    """Round like Excel ROUND() — .5 always rounds UP (vs Python banker's rounding)."""
    return math.floor(x + 0.5)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_overbooking_status(hotel, unit_type, check_in, ota_source=None):
    """
    Return a dict with full overbooking/occupancy analysis for a date:
        physical_rooms, safety_buffer, sellable_rooms,
        booked_rooms, in_house_arrivals, arrivals, expected_occupied,
        occupancy_pct, real_occupancy, exp_occ_for_pricing, lock_status, risk_level
    """
    check_in = getdate(check_in)

    physical_rooms = _get_physical_rooms(hotel, unit_type)
    if not physical_rooms:
        return _empty_status()

    hotel_data = frappe.db.get_value(
        "Customer", hotel,
        ["custom_safety_buffer_rate", "custom_lock_threshold_pct"],
        as_dict=True,
    )
    safety_buffer_rate = float(hotel_data.custom_safety_buffer_rate or 5) / 100 if hotel_data else 0.05
    lock_threshold = float(hotel_data.custom_lock_threshold_pct or 92) / 100 if hotel_data else 0.92

    no_show_rate = _get_no_show_rate(hotel, check_in) / 100

    no_show_rooms = _excel_round(physical_rooms * no_show_rate)
    safety_buffer = max(1, _excel_round(physical_rooms * safety_buffer_rate))
    sellable = max(1, physical_rooms + no_show_rooms - safety_buffer)

    # Date-based queries
    booked = get_booked_rooms_for_date(hotel, unit_type, check_in)
    in_house = get_in_house_and_arrivals(hotel, unit_type, check_in)
    arrivals = get_arrivals(hotel, unit_type, check_in)
    expected = get_expected_occupied(hotel, unit_type, check_in)

    # If no Hotel Reservation records exist, fall back to static counters
    if not in_house and not arrivals:
        _, static_booked = _get_room_counts(hotel, unit_type)
        if static_booked:
            expected = static_booked
            booked = static_booked

    occupancy_pct = expected / physical_rooms if physical_rooms else 0
    real_occupancy_pct = in_house / physical_rooms if physical_rooms else 0
    exp_occ_pricing = expected / sellable if sellable else 0

    locked = occupancy_pct >= lock_threshold
    lock_status = "LOCK" if locked else "OPEN"

    if locked or expected > sellable:
        risk_level = "HIGH"
    elif occupancy_pct >= 0.8:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "physical_rooms": physical_rooms,
        "safety_buffer": safety_buffer,
        "sellable_rooms": sellable,
        "booked_rooms": booked,
        "in_house_arrivals": in_house,
        "arrivals": arrivals,
        "expected_occupied": expected,
        "occupancy_pct": round(occupancy_pct * 100, 2),
        "real_occupancy": round(real_occupancy_pct * 100, 2),
        "exp_occ_for_pricing": round(exp_occ_pricing, 4),
        "lock_status": lock_status,
        "risk_level": risk_level,
    }


def get_daily_calendar(hotel, unit_type, from_date, to_date, ota_source=None):
    """
    Return a list of dicts (one per day) for the overbooking calendar report.
    ota_source is forwarded for pricing calculations but does not affect no-show rate.
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

def get_booked_rooms_for_date(hotel, unit_type, target_date, exclude_name=None):
    """
    Query Booking Intake (confirmed) where check_in == target_date.
    Returns total rooms from OTA/advance bookings arriving on that date.
    Pass exclude_name to exclude a specific Booking Intake document (e.g. the one being confirmed).
    """
    target_date = getdate(target_date)
    if exclude_name:
        result = frappe.db.sql("""
            SELECT COALESCE(SUM(ac.allocated_units), 0) as total
            FROM `tabBooking Intake` bi
            JOIN `tabAvailability Control` ac ON ac.parent = bi.name
            WHERE bi.hotel = %s
              AND ac.unit_type = %s
              AND bi.booking_status = 'Confirmed'
              AND bi.check_in = %s
              AND bi.name != %s
        """, (hotel, unit_type, target_date, exclude_name), as_dict=True)
    else:
        result = frappe.db.sql("""
            SELECT COALESCE(SUM(ac.allocated_units), 0) as total
            FROM `tabBooking Intake` bi
            JOIN `tabAvailability Control` ac ON ac.parent = bi.name
            WHERE bi.hotel = %s
              AND ac.unit_type = %s
              AND bi.booking_status = 'Confirmed'
              AND bi.check_in = %s
        """, (hotel, unit_type, target_date), as_dict=True)
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
    AND booking_source is set (any OTA source).
    Returns rooms arriving today that can no-show.
    """
    target_date = getdate(target_date)
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(number_of_rooms), 0) as total
        FROM `tabHotel Reservation`
        WHERE hotel = %s
          AND unit_type = %s
          AND status = 'مؤكد'
          AND check_in = %s
          AND booking_source IS NOT NULL
          AND booking_source != ''
    """, (hotel, unit_type, target_date), as_dict=True)
    return int(result[0].total) if result else 0


def get_expected_occupied(hotel, unit_type, target_date):
    """
    Expected Occupied = (Booked - Arrivals) - No-Show Rooms + In-House

    No-Show Rooms = (Booked - Arrivals) × No-Show Rate %  (no rounding — kept as float)
    i.e. the deduction is from the pending bookings pool, not from physical capacity.
    """
    target_date = getdate(target_date)
    ih = get_in_house_and_arrivals(hotel, unit_type, target_date)
    ar = get_arrivals(hotel, unit_type, target_date)
    bk = get_booked_rooms_for_date(hotel, unit_type, target_date)
    ns_rate = _get_no_show_rate(hotel, target_date) / 100
    pending = max(0, bk - ar)
    no_show_rooms = pending * ns_rate

    return max(0, pending - no_show_rooms) + ih


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


def _get_no_show_rate(hotel, check_in):
    """
    Return the applicable no-show rate % for a hotel on a given date.

    Priority:
      1. Hotel Season override (season covering the date with a rate defined)
      2. Hotel (Customer) default rate
      3. System default: 5%

    Weekend = Thursday and Friday (Middle East convention).
    """
    # ISO weekday: Mon=1 … Sun=7; Thu=4, Fri=5
    is_weekend = getdate(check_in).isoweekday() in (4, 5)

    # 1. Season override
    season = frappe.db.sql("""
        SELECT no_show_rate_weekday, no_show_rate_weekend
        FROM `tabHotel Season`
        WHERE hotel = %s
          AND start_date <= %s
          AND end_date >= %s
          AND (
              no_show_rate_weekday IS NOT NULL AND no_show_rate_weekday != 0
              OR no_show_rate_weekend IS NOT NULL AND no_show_rate_weekend != 0
          )
        ORDER BY start_date DESC
        LIMIT 1
    """, (hotel, check_in, check_in), as_dict=True)

    if season:
        s = season[0]
        rate = (s.no_show_rate_weekend or s.no_show_rate_weekday) if is_weekend \
               else (s.no_show_rate_weekday or s.no_show_rate_weekend)
        if rate:
            return float(rate)

    # 2. Hotel (Customer) default
    hotel_data = frappe.db.get_value(
        "Customer", hotel,
        ["custom_no_show_rate_weekday", "custom_no_show_rate_weekend"],
        as_dict=True,
    )
    if hotel_data:
        rate = (hotel_data.custom_no_show_rate_weekend or hotel_data.custom_no_show_rate_weekday) if is_weekend \
               else (hotel_data.custom_no_show_rate_weekday or hotel_data.custom_no_show_rate_weekend)
        if rate:
            return float(rate)

    # 3. System default
    return 5.0


def _empty_status():
    return {
        "physical_rooms": 0,
        "safety_buffer": 0,
        "sellable_rooms": 0,
        "booked_rooms": 0,
        "in_house_arrivals": 0,
        "arrivals": 0,
        "expected_occupied": 0,
        "occupancy_pct": 0,
        "real_occupancy": 0,
        "exp_occ_for_pricing": 0,
        "lock_status": "OPEN",
        "risk_level": "LOW",
    }
