# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HotelUnitType(Document):
    pass


@frappe.whitelist()
def get_unit_types_for_hotel(hotel):
    """
    Fetch unit type details from Hotel Unit Type for a given hotel.
    Returns a list of dicts with unit_type_ref, total_units, units_allowed_on_platforms.
    Used by Hotel Season JS to populate season_unit_rates and availability_control tables.
    """
    hotel_unit_type = frappe.db.get_value(
        "Hotel Unit Type", {"hotel": hotel}, "name"
    )
    if not hotel_unit_type:
        return []

    return frappe.get_all(
        "Hotel Unit Detail",
        filters={"parent": hotel_unit_type},
        fields=["unit_type_ref", "total_units", "units_allowed_on_platforms"],
    )
