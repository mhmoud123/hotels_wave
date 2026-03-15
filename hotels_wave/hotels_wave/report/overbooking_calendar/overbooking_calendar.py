# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

"""
Overbooking Calendar — Script Report.

Mirrors the DailyCalendar Excel sheet. Shows per-day overbooking status
for a hotel / unit type over a date range.
"""

import frappe
from frappe import _


from hotels_wave.hotels_wave.utils.overbooking_engine import get_daily_calendar
from hotels_wave.hotels_wave.utils.pricing_engine import calculate_dynamic_price, _get_active_season


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": _("Day"), "fieldname": "day_of_week", "fieldtype": "Data", "width": 90},
        {"label": _("Season"), "fieldname": "season_name", "fieldtype": "Data", "width": 150},
        {"label": _("Hotel"), "fieldname": "hotel", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": _("Unit Type"), "fieldname": "unit_type", "fieldtype": "Link", "options": "Unit Type", "width": 130},
        {"label": _("Physical Rooms"), "fieldname": "physical_rooms", "fieldtype": "Int", "width": 110},
        {"label": _("Sellable Rooms"), "fieldname": "sellable_rooms", "fieldtype": "Int", "width": 110},
        {"label": _("Booked Rooms"), "fieldname": "booked_rooms", "fieldtype": "Int", "width": 100},
        {"label": _("In-House"), "fieldname": "in_house_arrivals", "fieldtype": "Int", "width": 80},
        {"label": _("Arrivals"), "fieldname": "arrivals", "fieldtype": "Int", "width": 75},
        {"label": _("Expected Occ"), "fieldname": "expected_occupied", "fieldtype": "Float", "width": 100},
        {"label": _("Safety Buffer"), "fieldname": "safety_buffer", "fieldtype": "Int", "width": 100},
        {"label": _("Available"), "fieldname": "available_rooms", "fieldtype": "Int", "width": 90},
        {"label": _("Occupancy %"), "fieldname": "occupancy_pct", "fieldtype": "Percent", "width": 100},
        {"label": _("Real Occupancy"), "fieldname": "real_occupancy", "fieldtype": "Percent", "width": 110},
        {"label": _("Final Price"), "fieldname": "final_price", "fieldtype": "Currency", "width": 110},
        {"label": _("Lock Status"), "fieldname": "lock_status", "fieldtype": "Data", "width": 90},
        {"label": _("Risk Level"), "fieldname": "risk_level", "fieldtype": "Data", "width": 90},
    ]


def get_data(filters):
    hotel = filters.get("hotel")
    unit_type = filters.get("unit_type")
    ota_source = filters.get("ota_source")
    from_date = filters.get("from_date") or frappe.utils.today()
    to_date = filters.get("to_date") or frappe.utils.add_days(from_date, 30)

    if not hotel:
        return []

    # If no OTA source given, use the hotel's first active OTA for correct no-show rate
    if not ota_source:
        ota_source = frappe.db.get_value("OTA Account Setup", {"hotel": hotel}, "name")

    # Build list of unit types
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
    for ut in unit_types:
        calendar = get_daily_calendar(hotel, ut, from_date, to_date, ota_source)
        for entry in calendar:
            entry["hotel"] = hotel
            entry["unit_type"] = ut
            season_doc = _get_active_season(hotel, entry["date"])
            entry["season_name"] = frappe.db.get_value("Hotel Season", season_doc, "season_name_label") if season_doc else ""
            # Final Price from the pricing engine (1-night, defaults)
            pricing = calculate_dynamic_price(
                hotel=hotel,
                unit_type=ut,
                check_in=entry["date"],
                check_out=frappe.utils.add_days(entry["date"], 1),
                ota_source=ota_source,
            )
            entry["final_price"] = pricing.get("final_price", 0)
            # Available = Sellable - Booked (can go negative when overbooked)
            entry["available_rooms"] = entry.get("sellable_rooms", 0) - entry.get("booked_rooms", 0)
            rows.append(entry)

    # Sort by date then unit type
    rows.sort(key=lambda r: (r["date"], r.get("unit_type", "")))
    return rows
