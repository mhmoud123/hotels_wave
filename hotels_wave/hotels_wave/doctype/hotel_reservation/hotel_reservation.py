# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class HotelReservation(Document):

	def validate(self):
		self.validate_dates()
		self.validate_unit_type()

	def validate_dates(self):
		if self.check_in and self.check_out:
			if getdate(self.check_out) <= getdate(self.check_in):
				frappe.throw(_("Check Out must be after Check In."))

	def validate_unit_type(self):
		if not self.hotel or not self.unit_type:
			return
		hotel_unit_type = frappe.db.get_value("Hotel Unit Type", {"hotel": self.hotel}, "name")
		if not hotel_unit_type:
			frappe.throw(
				_("No Hotel Unit Type found for hotel {0}. Please set up unit types first.").format(self.hotel)
			)
		valid = frappe.db.exists(
			"Hotel Unit Detail",
			{"parent": hotel_unit_type, "unit_type_ref": self.unit_type},
		)
		if not valid:
			frappe.throw(
				_("Unit Type {0} does not exist in Hotel Unit Types for {1}.").format(
					self.unit_type, self.hotel
				)
			)
