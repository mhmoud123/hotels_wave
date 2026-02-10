// Copyright (c) 2024, Mahmoud Soliman and contributors
// For license information, please see license.txt

frappe.query_reports["Booking Report"] = {
    filters: [
        {
            fieldname: "hotel",
            label: __("Hotel"),
            fieldtype: "Link",
            options: "Hotel",
        },
        {
            fieldname: "ota_source",
            label: __("OTA Source"),
            fieldtype: "Link",
            options: "OTA Account Setup",
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "booking_status",
            label: __("Booking Status"),
            fieldtype: "Select",
            options: ["", "Open", "Confirmed", "Cancelled"],
        },
    ],
};
