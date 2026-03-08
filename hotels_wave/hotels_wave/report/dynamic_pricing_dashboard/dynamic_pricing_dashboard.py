# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

"""
Dynamic Pricing Dashboard — Unified Script Report.

Shows a daily calendar per hotel / unit type combining overbooking status
and all dynamic pricing factors in a single view (matches the Excel DailyCalendar sheet).
"""

import frappe
from frappe import _
from frappe.utils import getdate, add_days

from hotels_wave.hotels_wave.utils.pricing_engine import calculate_dynamic_price


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": _("Day"), "fieldname": "day_of_week", "fieldtype": "Data", "width": 80},
        {"label": _("Unit Type"), "fieldname": "unit_type", "fieldtype": "Link", "options": "Unit Type", "width": 130},
        # Overbooking columns
        {"label": _("Physical"), "fieldname": "physical_rooms", "fieldtype": "Int", "width": 75},
        {"label": _("Booked"), "fieldname": "booked_rooms", "fieldtype": "Int", "width": 70},
        {"label": _("In-House"), "fieldname": "in_house_arrivals", "fieldtype": "Int", "width": 80},
        {"label": _("Arrivals"), "fieldname": "arrivals", "fieldtype": "Int", "width": 75},
        {"label": _("Expected"), "fieldname": "expected_occupied", "fieldtype": "Float", "width": 80},
        {"label": _("Sellable"), "fieldname": "sellable_rooms", "fieldtype": "Int", "width": 75},
        {"label": _("Occ%"), "fieldname": "occ_pct", "fieldtype": "Percent", "width": 70},
        # Pricing columns
        {"label": _("Base Price"), "fieldname": "base_price", "fieldtype": "Currency", "width": 100},
        {"label": _("Season"), "fieldname": "f_seasonality", "fieldtype": "Float", "width": 75},
        {"label": _("DoW"), "fieldname": "f_day_of_week", "fieldtype": "Float", "width": 65},
        {"label": _("Lead Time"), "fieldname": "f_lead_time", "fieldtype": "Float", "width": 85},
        {"label": _("LOS"), "fieldname": "f_length_of_stay", "fieldtype": "Float", "width": 65},
        {"label": _("Segment"), "fieldname": "f_customer_segment", "fieldtype": "Float", "width": 80},
        {"label": _("Occ Yield"), "fieldname": "f_occupancy", "fieldtype": "Float", "width": 80},
        {"label": _("Demand"), "fieldname": "f_demand_pressure", "fieldtype": "Float", "width": 75},
        # Result columns
        {"label": _("Suggested"), "fieldname": "suggested_price", "fieldtype": "Currency", "width": 100},
        {"label": _("Final Price"), "fieldname": "final_price", "fieldtype": "Currency", "width": 100},
        {"label": _("Risk"), "fieldname": "risk_level", "fieldtype": "Data", "width": 70},
        {"label": _("Lock"), "fieldname": "lock_status", "fieldtype": "Data", "width": 65},
    ]


def get_data(filters):
    hotel = filters.get("hotel")
    unit_type = filters.get("unit_type")
    from_date = getdate(filters.get("from_date") or frappe.utils.today())
    to_date = getdate(filters.get("to_date") or frappe.utils.add_days(from_date, 7))
    ota_source = filters.get("ota_source")
    pricing_plan = filters.get("pricing_plan")
    customer_segment = filters.get("customer_segment")

    if not hotel:
        return []

    # Build list of unit types to show
    if unit_type:
        unit_types = [unit_type]
    else:
        hut = frappe.db.get_value("Hotel Unit Type", {"hotel": hotel}, "name")
        if hut:
            unit_types = frappe.get_all(
                "Hotel Unit Detail", filters={"parent": hut}, pluck="unit_type_ref"
            )
        else:
            unit_types = []

    rows = []
    current = from_date
    while current <= to_date:
        check_out = add_days(current, 1)
        for ut in unit_types:
            result = calculate_dynamic_price(
                hotel=hotel,
                unit_type=ut,
                check_in=current,
                check_out=check_out,
                ota_source=ota_source,
                pricing_plan=pricing_plan,
                customer_segment=customer_segment,
                units_in_booking=1,
            )
            fb = result.get("factor_breakdown", {})
            ob = result.get("overbooking_status", {})
            rows.append({
                "date": str(current),
                "day_of_week": current.strftime("%A"),
                "unit_type": ut,
                # Overbooking
                "physical_rooms": ob.get("physical_rooms", 0),
                "booked_rooms": ob.get("booked_rooms", 0),
                "in_house_arrivals": ob.get("in_house_arrivals", 0),
                "arrivals": ob.get("arrivals", 0),
                "expected_occupied": ob.get("expected_occupied", 0),
                "sellable_rooms": ob.get("sellable_rooms", 0),
                "occ_pct": ob.get("adj_occupancy_pct", 0),
                # Pricing factors
                "base_price": result.get("base_price", 0),
                "f_seasonality": round(fb.get("seasonality", 1.0), 4),
                "f_day_of_week": round(fb.get("day_of_week", 1.0), 4),
                "f_lead_time": round(fb.get("lead_time", 1.0), 4),
                "f_length_of_stay": round(fb.get("length_of_stay", 1.0), 4),
                "f_customer_segment": round(fb.get("customer_segment", 1.0), 4),
                "f_occupancy": round(fb.get("occupancy", 1.0), 4),
                "f_demand_pressure": round(fb.get("demand_pressure", 1.0), 4),
                # Results
                "suggested_price": result.get("suggested_price", 0),
                "final_price": result.get("final_price", 0),
                "risk_level": ob.get("risk_level", ""),
                "lock_status": ob.get("lock_status", ""),
            })
        current = add_days(current, 1)

    return rows
