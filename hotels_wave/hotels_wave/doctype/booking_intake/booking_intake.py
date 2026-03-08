# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, now_datetime, date_diff, getdate


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

	def before_save(self):
		"""Compute pricing fields before saving."""
		self._compute_lead_time()
		self._compute_length_of_stay()
		self._compute_suggested_price()

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

	def _compute_lead_time(self):
		"""Set lead_time_days = check_in - booking_date (creation date or today)."""
		if self.check_in:
			from datetime import date
			booking_date = getdate(self.creation) if self.creation else date.today()
			self.lead_time_days = max(0, (getdate(self.check_in) - booking_date).days)

	def _compute_length_of_stay(self):
		"""Set length_of_stay_nights = check_out - check_in."""
		if self.check_in and self.check_out:
			nights = date_diff(self.check_out, self.check_in)
			self.length_of_stay_nights = max(1, nights)

	def _compute_suggested_price(self):
		"""
		Calculate total suggested price for the entire booking by summing
		the dynamic price across every row in availability_control.

		Formula per row:
		    line_total = final_price_per_night × allocated_units × nights
		"""
		if not (self.hotel and self.check_in and self.check_out):
			return
		if not self.get("availability_control"):
			return

		try:
			from hotels_wave.hotels_wave.utils.pricing_engine import calculate_dynamic_price
			from datetime import date as _date

			nights = max(1, date_diff(self.check_out, self.check_in))
			booking_date = getdate(self.creation) if self.creation else _date.today()
			total_base   = 0.0
			total_final  = 0.0
			total_units  = 0
			weighted_factor = 0.0

			for row in self.availability_control:
				if not row.unit_type:
					continue
				units = row.allocated_units or 1

				result = calculate_dynamic_price(
					hotel=self.hotel,
					unit_type=row.unit_type,
					check_in=self.check_in,
					check_out=self.check_out,
					ota_source=self.ota_source,
					pricing_plan=self.pricing_plan,
					customer_segment=self.customer_segment,
					units_in_booking=units,
					booking_date=booking_date,
				)

				# Per-night × rooms × nights = line total
				total_base  += (result.get("base_price")  or 0) * units * nights
				total_final += (result.get("final_price") or 0) * units * nights
				weighted_factor += (result.get("composite_factor") or 1.0) * units
				total_units += units

			if total_units:
				self.computed_base_price  = total_base
				self.applied_price_factor = weighted_factor / total_units
				self.suggested_price      = total_final

		except Exception:
			frappe.log_error(frappe.get_traceback(), "Pricing Engine Error")

	def validate_availability(self):
		"""
		Check if this booking would cause overbooking for any unit type
		in the availability_control child table.
		Uses the overbooking engine for enriched risk assessment.
		Warns the user (msgprint) but does NOT block the save.
		"""
		if not self.hotel or not self.check_in or not self.check_out:
			return

		if not self.get("availability_control"):
			return

		hotel_unit_type = self._get_hotel_unit_type_name()
		if not hotel_unit_type:
			return

		try:
			from hotels_wave.hotels_wave.utils.overbooking_engine import get_overbooking_status
		except ImportError:
			get_overbooking_status = None

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

			allocated = row.allocated_units or 1

			# Enhanced overbooking check via overbooking engine
			if get_overbooking_status:
				ob = get_overbooking_status(self.hotel, row.unit_type, self.check_in, self.ota_source)
				if ob.get("lock_status") == "LOCK":
					frappe.msgprint(
						_(
							"Unit Type {0}: Bookings are LOCKED for {1} on {2}. "
							"Sellable rooms ({3}) are fully allocated. Risk: {4}."
						).format(
							row.unit_type, self.hotel, self.check_in,
							ob.get("sellable_rooms", 0), ob.get("risk_level", "HIGH"),
						),
						title=_("Overbooking Lock Warning"),
						indicator="red",
					)
				elif ob.get("risk_level") in ("HIGH", "MEDIUM"):
					frappe.msgprint(
						_(
							"Unit Type {0}: {1} overbooking risk for {2} on {3}. "
							"Occupancy: {4}%. Sellable: {5}."
						).format(
							row.unit_type, ob.get("risk_level"), self.hotel, self.check_in,
							ob.get("adj_occupancy_pct", 0), ob.get("sellable_rooms", 0),
						),
						title=_("Overbooking Risk Warning"),
						indicator="orange",
					)
			elif (detail.units_allowed_on_platforms or 0) < allocated:
				current_overbooked = detail.overbooked or 0
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

	def create_hotel_reservation(self):
		"""Create Hotel Reservation records when guest checks in (bridge from OTA booking)."""
		if not self.hotel or not self.get("availability_control"):
			return

		booking_source = self._get_booking_source_from_ota()
		created = []

		for row in self.availability_control:
			if not row.unit_type:
				continue
			reservation = frappe.get_doc({
				"doctype": "Hotel Reservation",
				"hotel": self.hotel,
				"unit_type": row.unit_type,
				"status": "مؤكد",
				"check_in_status": "تسجيل دخول",
				"booking_source": booking_source,
				"rental_type": "يومي",
				"check_in": self.check_in,
				"check_out": self.check_out,
				"number_of_rooms": row.allocated_units or 1,
				"guest_name": self.guest_name if hasattr(self, "guest_name") else None,
				"booking_intake": self.name,
			})
			reservation.insert(ignore_permissions=True)
			created.append(reservation.name)

		if created:
			frappe.msgprint(
				_("Created {0} Hotel Reservation(s): {1}").format(len(created), ", ".join(created)),
				title=_("Reservations Created"),
				indicator="green",
			)
		return created

	def _get_booking_source_from_ota(self):
		"""Map OTA Account Setup name to Hotel Reservation booking_source select value."""
		if not self.ota_source:
			return "اخرى"
		ota_name = frappe.db.get_value("OTA Account Setup", self.ota_source, "ota_name")
		if not ota_name:
			return "اخرى"
		ota_lower = (ota_name or "").lower().strip()
		if "booking" in ota_lower or "بوكينج" in ota_lower or "بوكنج" in ota_lower:
			return "Booking"
		if "expedia" in ota_lower:
			return "Expedia"
		return "اخرى"

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
def create_reservation_from_booking(booking_name):
	"""Whitelisted method to create Hotel Reservation from a Booking Intake."""
	booking = frappe.get_doc("Booking Intake", booking_name)
	return booking.create_hotel_reservation()


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
		