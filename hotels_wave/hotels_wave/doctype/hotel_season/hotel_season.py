# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class HotelSeason(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		end_date: DF.Date | None
		hotel: DF.Link | None
		season_type: DF.Literal["High", "Mid", "Low"]
		seasonal_commission: DF.Percent
		start_date: DF.Date | None
	# end: auto-generated types

	def validate(self):
		"""Validate season dates and check for overlaps."""
		self.validate_dates()
		self.validate_no_overlap()

	def validate_dates(self):
		"""Ensure start_date is before end_date."""
		if self.start_date and self.end_date:
			if getdate(self.start_date) > getdate(self.end_date):
				frappe.throw(
					_("Start Date ({0}) must be before End Date ({1}).").format(
						self.start_date, self.end_date
					)
				)

	def validate_no_overlap(self):
		"""Prevent overlapping seasons for the same hotel."""
		if not self.hotel or not self.start_date or not self.end_date:
			return

		overlapping = frappe.db.sql(
			"""
			SELECT name, season_type, start_date, end_date
			FROM `tabHotel Season`
			WHERE hotel = %(hotel)s
				AND name != %(name)s
				AND start_date <= %(end_date)s
				AND end_date >= %(start_date)s
			""",
			{
				"hotel": self.hotel,
				"name": self.name or "",
				"start_date": self.start_date,
				"end_date": self.end_date,
			},
			as_dict=True,
		)

		if overlapping:
			season = overlapping[0]
			frappe.throw(
				_("This season overlaps with {0} ({1}: {2} to {3}). "
				  "A hotel cannot have two seasons active on the same dates.").format(
					season.name, season.season_type,
					season.start_date, season.end_date
				)
			)
