# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, date_diff


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_columns():
	return [
		{
			"fieldname": "hotel",
			"label": _("Hotel"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180,
		},
		{
			"fieldname": "total_bookings",
			"label": _("Total Bookings"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "total_nights",
			"label": _("Total Nights"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "total_revenue",
			"label": _("Total Revenue"),
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"fieldname": "adr",
			"label": _("Avg Daily Rate"),
			"fieldtype": "Currency",
			"width": 130,
		},
	]


def get_data(filters):
	conditions = get_conditions(filters)

	result = []
	hotel_map = {}

	# Fetch individual confirmed bookings to calculate nights and aggregate
	individual_bookings = frappe.db.sql(
		f"""
		SELECT
			hotel,
			total_value,
			check_in,
			check_out
		FROM `tabBooking Intake`
		WHERE booking_status = 'Confirmed' {conditions}
		""",
		filters,
		as_dict=True,
	)

	for booking in individual_bookings:
		key = booking.hotel
		if key not in hotel_map:
			hotel_map[key] = {
				"hotel": booking.hotel,
				"total_bookings": 0,
				"total_nights": 0,
				"total_revenue": 0,
			}

		hotel_map[key]["total_bookings"] += 1
		hotel_map[key]["total_revenue"] += flt(booking.total_value)

		# Calculate nights
		if booking.check_in and booking.check_out:
			nights = date_diff(booking.check_out, booking.check_in)
			hotel_map[key]["total_nights"] += nights if nights > 0 else 1

	# Calculate ADR for each group
	for key, row in hotel_map.items():
		if row["total_nights"] > 0:
			row["adr"] = flt(row["total_revenue"]) / row["total_nights"]
		else:
			row["adr"] = 0
		result.append(row)

	# Sort by hotel
	result.sort(key=lambda x: (x["hotel"] or ""))

	return result


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

	return conditions


def get_chart(data):
	"""Generate a chart showing revenue by hotel."""
	if not data:
		return None

	# Aggregate revenue by hotel
	hotel_revenue = {}
	for row in data:
		hotel = row.get("hotel") or "Unknown"
		if hotel not in hotel_revenue:
			hotel_revenue[hotel] = 0
		hotel_revenue[hotel] += flt(row.get("total_revenue"))

	labels = list(hotel_revenue.keys())
	values = list(hotel_revenue.values())

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Revenue"), "values": values}],
		},
		"type": "bar",
		"colors": ["#5e64ff"],
	}
