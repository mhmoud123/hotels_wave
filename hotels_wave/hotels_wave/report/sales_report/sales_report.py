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
			"fieldname": "unit_type",
			"label": _("Unit Type"),
			"fieldtype": "Link",
			"options": "Unit Type",
			"width": 130,
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

	# Fetch confirmed bookings with their availability_control child rows
	bookings = frappe.db.sql(
		f"""
		SELECT
			bi.name,
			bi.hotel,
			bi.total_value,
			bi.check_in,
			bi.check_out,
			ac.unit_type,
			ac.allocated_units
		FROM `tabBooking Intake` bi
		LEFT JOIN `tabAvailability Control` ac ON ac.parent = bi.name
		WHERE bi.booking_status = 'Confirmed' {conditions}
		ORDER BY bi.hotel, ac.unit_type
		""",
		filters,
		as_dict=True,
	)

	group_map = {}

	for row in bookings:
		unit_type = row.unit_type or "—"
		key = (row.hotel, unit_type)

		if key not in group_map:
			group_map[key] = {
				"hotel": row.hotel,
				"unit_type": unit_type,
				"total_bookings": 0,
				"total_nights": 0,
				"total_revenue": 0,
				"_seen_bookings": set(),
			}

		grp = group_map[key]

		# Count each booking only once per group
		if row.name not in grp["_seen_bookings"]:
			grp["_seen_bookings"].add(row.name)
			grp["total_bookings"] += 1

		nights = 1
		if row.check_in and row.check_out:
			nights = max(1, date_diff(row.check_out, row.check_in))

		units = row.allocated_units or 1
		grp["total_nights"] += nights * units
		grp["total_revenue"] += flt(row.total_value) * units / max(1, _count_unit_rows(row.name, bookings))

	# Calculate ADR and build result
	result = []
	for key, grp in group_map.items():
		grp.pop("_seen_bookings", None)
		if grp["total_nights"] > 0:
			grp["adr"] = flt(grp["total_revenue"]) / grp["total_nights"]
		else:
			grp["adr"] = 0
		result.append(grp)

	result.sort(key=lambda x: (x["hotel"] or "", x["unit_type"] or ""))
	return result


def _count_unit_rows(booking_name, bookings):
	"""Count how many availability_control rows belong to a given booking."""
	return sum(1 for b in bookings if b.name == booking_name)


def get_conditions(filters):
	conditions = ""

	if filters.get("hotel"):
		conditions += " AND bi.hotel = %(hotel)s"

	if filters.get("ota_source"):
		conditions += " AND bi.ota_source = %(ota_source)s"

	if filters.get("from_date"):
		conditions += " AND bi.check_in >= %(from_date)s"

	if filters.get("to_date"):
		conditions += " AND bi.check_out <= %(to_date)s"

	return conditions


def get_chart(data):
	"""Generate a chart showing revenue by hotel."""
	if not data:
		return None

	# Aggregate revenue by hotel for chart
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
