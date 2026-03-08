frappe.query_reports["Overbooking Calendar"] = {
    "filters": [
        {
            "fieldname": "hotel",
            "label": "Hotel",
            "fieldtype": "Link",
            "options": "Customer",
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), 1),
            "reqd": 1
        },
        {
            "fieldname": "unit_type",
            "label": "Unit Type",
            "fieldtype": "Link",
            "options": "Unit Type"
        }
    ],
}