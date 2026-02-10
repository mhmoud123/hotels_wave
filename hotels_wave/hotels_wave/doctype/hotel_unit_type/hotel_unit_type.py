# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class HotelUnitType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from hotels_wave.hotels_wave.doctype.hotel_unit_detail.hotel_unit_detail import HotelUnitDetail

		hotel: DF.Link | None
		units_list: DF.Table[HotelUnitDetail]
	# end: auto-generated types

	pass


@frappe.whitelist()
def get_unit_types_for_hotel(hotel):
	"""
	Fetch unit type details from Hotel Unit Type for a given hotel.
	Returns a list of dicts with unit_type, total_units, units_allowed_on_platforms.
	Used by Hotel Season JS to populate season_unit_rates and availability_control tables.
	"""
	hotel_unit_type = frappe.db.get_value(
		"Hotel Unit Type", {"hotel": hotel}, "name"
	)

	if not hotel_unit_type:
		return []

	unit_details = frappe.get_all(
		"Hotel Unit Detail",
		filters={"parent": hotel_unit_type},
		fields=["unit_type_ref", "total_units", "units_allowed_on_platforms"],
	)

	return unit_details
