# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

"""
Whitelisted API endpoints for the Dynamic Pricing system.
Called from Booking Intake JS and report scripts.
"""

import json

import frappe
from frappe.utils import date_diff, flt

from hotels_wave.hotels_wave.utils.pricing_engine import calculate_dynamic_price
from hotels_wave.hotels_wave.utils.overbooking_engine import (
    get_overbooking_status,
    get_daily_calendar,
)


@frappe.whitelist()
def get_suggested_price(
    hotel,
    unit_type,
    check_in,
    check_out,
    ota_source=None,
    pricing_plan=None,
    customer_segment=None,
    units_in_booking=1,
    booking_date=None,
):
    """
    Called from Booking Intake form JS to get the suggested price.
    Returns a dict with base_price, suggested_price, final_price,
    factor_breakdown, overbooking_status, lead_time_days, length_of_stay_nights.
    """
    try:
        units_in_booking = int(units_in_booking or 1)
    except (ValueError, TypeError):
        units_in_booking = 1

    return calculate_dynamic_price(
        hotel=hotel,
        unit_type=unit_type,
        check_in=check_in,
        check_out=check_out,
        ota_source=ota_source,
        pricing_plan=pricing_plan,
        customer_segment=customer_segment,
        units_in_booking=units_in_booking,
        booking_date=booking_date,
    )


@frappe.whitelist()
def get_booking_pricing(
    hotel,
    check_in,
    check_out,
    availability_rows,
    ota_source=None,
    pricing_plan=None,
    customer_segment=None,
    booking_date=None,
):
    """
    Price the entire booking in one call.

    `availability_rows` is a JSON list of {unit_type, allocated_units} objects
    (the availability_control child table rows).

    Returns:
        total_base_price      — sum of base_price × units × nights (all rows)
        total_suggested_price — sum of final_price × units × nights (all rows)
        composite_factor      — weighted average across rows
        lead_time_days
        length_of_stay_nights
        rows                  — per-row breakdown for display
        worst_overbooking     — highest-risk row's overbooking status dict
    """
    if isinstance(availability_rows, str):
        availability_rows = json.loads(availability_rows)

    nights = max(1, date_diff(check_out, check_in))

    total_base   = 0.0
    total_final  = 0.0
    total_units  = 0
    weighted_f   = 0.0
    rows_out     = []
    worst_ob     = None
    risk_rank    = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

    for row in availability_rows:
        unit_type = row.get("unit_type")
        units     = int(row.get("allocated_units") or 1)
        if not unit_type:
            continue

        result = calculate_dynamic_price(
            hotel=hotel,
            unit_type=unit_type,
            check_in=check_in,
            check_out=check_out,
            ota_source=ota_source,
            pricing_plan=pricing_plan,
            customer_segment=customer_segment,
            units_in_booking=units,
            booking_date=booking_date,
        )

        line_base  = (result.get("base_price")  or 0) * units * nights
        line_final = (result.get("final_price") or 0) * units * nights
        factor     = result.get("composite_factor") or 1.0

        total_base  += line_base
        total_final += line_final
        weighted_f  += factor * units
        total_units += units

        ob = result.get("overbooking_status") or {}
        if worst_ob is None or risk_rank.get(ob.get("risk_level", "LOW"), 0) > risk_rank.get(worst_ob.get("risk_level", "LOW"), 0):
            worst_ob = ob
        rows_out.append({
            "unit_type":         unit_type,
            "allocated_units":   units,
            "base_price":        result.get("base_price", 0),
            "final_price":       result.get("final_price", 0),
            "line_total":        line_final,
            "composite_factor":  factor,
            "lead_time_days":    result.get("lead_time_days", 0),
            "factor_breakdown":  result.get("factor_breakdown", {}),
            "overbooking":       ob,
        })

    avg_factor = flt(weighted_f / total_units) if total_units else 1.0

    suggested_price = flt(total_final)
    return {
        "total_base_price":      total_base,
        "total_suggested_price": suggested_price,
        "composite_factor":      avg_factor,
        "lead_time_days":        rows_out[0].get("lead_time_days", 0) if rows_out else 0,
        "length_of_stay_nights": nights,
        "rows":                  rows_out,
        "worst_overbooking":     worst_ob or {},
    }


@frappe.whitelist()
def get_overbooking_status_for_date(hotel, unit_type, check_in, ota_source=None):
    """
    Single-date overbooking status. Used by Booking Intake dashboard indicator.
    """
    return get_overbooking_status(
        hotel=hotel,
        unit_type=unit_type,
        check_in=check_in,
        ota_source=ota_source,
    )


@frappe.whitelist()
def get_overbooking_dashboard(hotel, unit_type, from_date, to_date):
    """
    Multi-day overbooking calendar for reports.
    """
    return get_daily_calendar(
        hotel=hotel,
        unit_type=unit_type,
        from_date=from_date,
        to_date=to_date,
    )
