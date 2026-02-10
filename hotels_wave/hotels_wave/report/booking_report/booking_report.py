# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, date_diff


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("Booking Ref"),
			"fieldtype": "Link",
			"options": "Booking Intake",
			"width": 140,
		},
		{
			"fieldname": "ota_source",
			"label": _("Source"),
			"fieldtype": "Link",
			"options": "OTA Account Setup",
			"width": 150,
		},
		{
			"fieldname": "creation",
			"label": _("Creation Date"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "booking_status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "hotel",
			"label": _("Hotel"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
		},
		{
			"fieldname": "nights",
			"label": _("Nights"),
			"fieldtype": "Int",
			"width": 70,
		},
		{
			"fieldname": "total_value",
			"label": _("Total Value"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"fieldname": "adr",
			"label": _("Avg Daily Rate"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"fieldname": "check_in",
			"label": _("Check In"),
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"fieldname": "check_out",
			"label": _("Check Out"),
			"fieldtype": "Date",
			"width": 100,
		},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	bookings = frappe.db.sql(
		f"""
		SELECT
			name,
			ota_source,
			DATE(creation) as creation,
			booking_status,
			hotel,
			total_value,
			check_in,
			check_out
		FROM `tabBooking Intake`
		WHERE 1=1 {conditions}
		ORDER BY creation DESC
		""",
		filters,
		as_dict=True,
	)

	for row in bookings:
		# Calculate nights
		if row.check_in and row.check_out:
			nights = date_diff(row.check_out, row.check_in)
			row["nights"] = nights if nights > 0 else 1
		else:
			row["nights"] = 0

		# Calculate ADR (Average Daily Rate)
		if row["nights"] > 0 and row.total_value:
			row["adr"] = flt(row.total_value) / row["nights"]
		else:
			row["adr"] = 0

	return bookings


def get_conditions(filters):
	conditions = ""

	if filters.get("hotel"):
		conditions += " AND hotel = %(hotel)s"

	if filters.get("ota_source"):
		conditions += " AND ota_source = %(ota_source)s"

	if filters.get("from_date"):
		conditions += " AND check_in >= %(from_date)s"

	if filters.get("to_date"):
		conditions += " AND check_out <= %(to_date)s"

	if filters.get("booking_status"):
		conditions += " AND booking_status = %(booking_status)s"

	return conditions
