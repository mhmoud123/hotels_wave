# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, now_datetime


class BookingIntake(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		booking_status: DF.Literal["Open", "Confirmed", "Cancelled"]
		check_in: DF.Date | None
		check_out: DF.Date | None
		currency: DF.Link | None
		external_id: DF.Data | None
		hotel: DF.Link | None
		ota_source: DF.Link | None
		total_value: DF.Currency
		unit_type: DF.Link | None
	# end: auto-generated types

	def _get_hotel_unit_type_name(self):
		"""Get the Hotel Unit Type name for this booking's hotel. Shared helper to avoid repeated lookups."""
		if not self.hotel:
			return None
		return frappe.db.get_value("Hotel Unit Type", {"hotel": self.hotel}, "name")

	def before_insert(self):
		"""Set default status to 'Open' for new bookings."""
		if not self.booking_status:
			self.booking_status = "Open"

	def validate(self):
		"""Validate availability and unit types before saving."""
		self.validate_availability_control_unit_types()
		self.validate_availability()

	def on_submit(self):
		"""Handle confirm on initial submit."""
		if self.booking_status == "Confirmed":
			self.on_booking_confirmed()

	def on_update_after_submit(self):
		"""Handle status changes after submit (booking_status is allow_on_submit)."""
		previous_doc = self.get_doc_before_save()
		if not previous_doc:
			return

		old_status = previous_doc.booking_status
		new_status = self.booking_status

		if old_status != new_status:
			if new_status == "Confirmed":
				self.on_booking_confirmed()
			elif old_status == "Confirmed" and new_status == "Cancelled":
				self.on_booking_cancelled()

	def validate_availability(self):
		"""
		Check if this booking would cause overbooking for any unit type
		in the availability_control child table.
		Warns the user (msgprint) but does NOT block the save.
		"""
		if not self.hotel or not self.check_in or not self.check_out:
			return

		if not self.get("availability_control"):
			return

		hotel_unit_type = self._get_hotel_unit_type_name()
		if not hotel_unit_type:
			return

		for row in self.availability_control:
			if not row.unit_type:
				continue

			detail = frappe.db.get_value(
				"Hotel Unit Detail",
				{"parent": hotel_unit_type, "unit_type_ref": row.unit_type},
				["units_allowed_on_platforms", "overbooked"],
				as_dict=True,
			)

			if not detail:
				continue

			# If units_allowed is 0 or less than what this booking needs,
			# this booking will cause overbooking
			allocated = row.allocated_units or 1
			if (detail.units_allowed_on_platforms or 0) < allocated:
				current_overbooked = detail.overbooked or 0
				will_overbook_by = allocated - (detail.units_allowed_on_platforms or 0)
				frappe.msgprint(
					_(
						"Unit Type {0}: This booking is over the limit. "
						"Only {1} units available on platforms for {2}. "
						"This booking needs {3} units. Currently overbooked by {4}."
					).format(
						row.unit_type,
						detail.units_allowed_on_platforms or 0,
						self.hotel,
						allocated,
						current_overbooked,
					),
					title=_("Overbooking Warning"),
					indicator="orange",
				)

	def validate_availability_control_unit_types(self):
		"""
		Validate that each unit_type in the availability_control child table
		exists in the Hotel Unit Types for the selected hotel.
		"""
		if not self.hotel or not self.get("availability_control"):
			return

		hotel_unit_type = self._get_hotel_unit_type_name()
		if not hotel_unit_type:
			frappe.throw(
				_("No Hotel Unit Type found for hotel {0}. Please set up unit types first.").format(self.hotel)
			)

		# Get all valid unit types for this hotel
		valid_unit_types = frappe.get_all(
			"Hotel Unit Detail",
			filters={"parent": hotel_unit_type},
			pluck="unit_type_ref",
		)

		for row in self.availability_control:
			if row.unit_type and row.unit_type not in valid_unit_types:
				frappe.throw(
					_("Unit Type {0} (Row {1}) does not exist in Hotel Unit Types for {2}.").format(
						row.unit_type, row.idx, self.hotel
					)
				)

	def on_booking_confirmed(self):
		"""
		When a booking is confirmed, for each unit type in availability_control:
		decrement units_allowed_on_platforms (min 0), then increment overbooked.
		"""
		if not self.hotel or not self.get("availability_control"):
			return

		hotel_unit_type = self._get_hotel_unit_type_name()
		if not hotel_unit_type:
			return

		for row in self.availability_control:
			if not row.unit_type:
				continue
			detail_name = frappe.db.get_value(
				"Hotel Unit Detail",
				{"parent": hotel_unit_type, "unit_type_ref": row.unit_type},
				"name",
			)
			if not detail_name:
				continue

			detail = frappe.get_doc("Hotel Unit Detail", detail_name)
			if detail.units_allowed_on_platforms and detail.units_allowed_on_platforms > 0:
				detail.units_allowed_on_platforms -= row.allocated_units
				if detail.units_allowed_on_platforms < 0:
					detail.overbooked += abs(detail.units_allowed_on_platforms)
					detail.units_allowed_on_platforms = 0
			else:
				detail.overbooked += row.allocated_units

			detail.save(ignore_permissions=True)

	def on_booking_cancelled(self):
		"""
		When a confirmed booking is cancelled, for each unit type in availability_control:
		decrement overbooked first (if > 0), otherwise increment units_allowed_on_platforms.
		"""
		if not self.hotel or not self.get("availability_control"):
			return

		hotel_unit_type = self._get_hotel_unit_type_name()
		if not hotel_unit_type:
			return

		for row in self.availability_control:
			if not row.unit_type:
				continue

			detail_name = frappe.db.get_value(
				"Hotel Unit Detail",
				{"parent": hotel_unit_type, "unit_type_ref": row.unit_type},
				"name",
			)
			if not detail_name:
				continue

			detail = frappe.get_doc("Hotel Unit Detail", detail_name)
			allocated = row.allocated_units or 1
			if detail.overbooked and detail.overbooked > 0:
				restore_from_overbooked = min(allocated, detail.overbooked)
				detail.overbooked -= restore_from_overbooked
				remainder = allocated - restore_from_overbooked
				detail.units_allowed_on_platforms = (detail.units_allowed_on_platforms or 0) + remainder
			else:
				detail.units_allowed_on_platforms = (detail.units_allowed_on_platforms or 0) + allocated

			detail.save(ignore_permissions=True)


@frappe.whitelist()
def auto_confirm_bookings():
	"""
	Scheduled job to automatically confirm bookings that have been
	in 'Open' status for more than 24 hours.
	"""
	cutoff_time = add_days(now_datetime(), -1)

	open_bookings = frappe.get_all(
		"Booking Intake",
		filters={
			"booking_status": "Open",
			"creation": ["<", cutoff_time],
		},
		pluck="name",
	)

	confirmed_count = 0
	failed_count = 0

	for booking_name in open_bookings:
		try:
			booking = frappe.get_doc("Booking Intake", booking_name)
			booking.booking_status = "Confirmed"
			booking.save(ignore_permissions=True)
			confirmed_count += 1
		except frappe.ValidationError as e:
			# Log the error but continue with other bookings
			frappe.log_error(
				message=str(e),
				title=f"Auto-confirm failed for {booking_name}",
			)
			failed_count += 1

	frappe.db.commit()

	if confirmed_count > 0 or failed_count > 0:
		frappe.logger().info(
			f"Auto-confirm bookings: {confirmed_count} confirmed, {failed_count} failed"
		)

	return {"confirmed": confirmed_count, "failed": failed_count}
		