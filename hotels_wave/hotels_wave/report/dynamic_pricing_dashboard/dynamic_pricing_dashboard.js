frappe.query_reports["Dynamic Pricing Dashboard"] = {
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
        },
        {
            "fieldname": "ota_source",
            "label": "OTA Source",
            "fieldtype": "Link",
            "options": "OTA Account Setup"
        },
        {
            "fieldname": "pricing_plan",
            "label": "Pricing Plan",
            "fieldtype": "Link",
            "options": "Pricing Plan"
        },
        {
            "fieldname": "customer_segment",
            "label": "Customer Segment",
            "fieldtype": "Select",
            "options": "\nB2C\nB2B\nGroup\nGovernment"
        }
    ],
}