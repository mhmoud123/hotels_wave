# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class HotelUnitDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cancellation_policy: DF.SmallText | None
		features: DF.SmallText | None
		max_occupancy: DF.Int
		min_stay: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		total_units: DF.Int
		unit_type_ref: DF.Link | None
		units_allowed_on_platforms: DF.Int
	# end: auto-generated types

	pass
