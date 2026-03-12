# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _


@frappe.whitelist()
def get_channel_target_data(from_date, to_date):
	"""Return existing Channel Day Entry records keyed by {channel}-{date}."""
	records = frappe.get_all(
		"Channel Day Entry",
		filters={"date": ["between", [from_date, to_date]]},
		fields=["channel", "date", "value"],
	)

	result = {}
	for r in records:
		key = f"{r.channel}-{r.date}"
		result[key] = r.value

	return result


@frappe.whitelist()
def save_channel_targets(entries):
	"""Bulk upsert Channel Day Entry records.

	Args:
	    entries: JSON string — list of {channel, date, value}
	"""
	if isinstance(entries, str):
		entries = json.loads(entries)

	for entry in entries:
		channel = entry.get("channel")
		date = entry.get("date")
		value = entry.get("value", 0)
		name = f"{channel}-{date}"

		if frappe.db.exists("Channel Day Entry", name):
			frappe.db.set_value("Channel Day Entry", name, "value", value)
		else:
			doc = frappe.get_doc({
				"doctype": "Channel Day Entry",
				"channel": channel,
				"date": date,
				"value": value,
			})
			doc.insert()

	frappe.db.commit()
	return {"message": _("Saved {0} entries").format(len(entries))}
