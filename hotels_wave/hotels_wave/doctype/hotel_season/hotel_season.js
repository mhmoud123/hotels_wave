// Copyright (c) 2026, Mahmoud Soliman and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hotel Season", {
    refresh(frm) {
        frm.add_custom_button(__("Create Campaign"), function () {
            frappe.set_route("Form", "Campaign", "new-campaign-1");
        }, __("Actions"));
    },

    hotel(frm) {
        // When hotel changes, fetch unit types and populate tables
        if (!frm.doc.hotel) {
            return;
        }

        frappe.call({
            method: "hotels_wave.hotels_wave.doctype.hotel_unit_type.hotel_unit_type.get_unit_types_for_hotel",
            args: { hotel: frm.doc.hotel },
            callback: function (r) {
                if (r.message && r.message.length > 0) {
                    // Clear existing rows
                    frm.clear_table("season_unit_rates");
                    frm.clear_table("availability_control");

                    r.message.forEach(function (unit) {
                        // Populate Season Unit Rates
                        let rate_row = frm.add_child("season_unit_rates");
                        rate_row.unit_type = unit.unit_type_ref;

                        // Populate Availability Control
                        let avail_row = frm.add_child("availability_control");
                        avail_row.unit_type = unit.unit_type_ref;
                        avail_row.allocated_units = unit.units_allowed_on_platforms || 0;
                    });

                    frm.refresh_fields();
                    frappe.show_alert({
                        message: __("{0} unit type(s) fetched from Hotel Unit Types", [r.message.length]),
                        indicator: "green"
                    });
                } else {
                    frappe.show_alert({
                        message: __("No unit types found for this hotel in Hotel Unit Types"),
                        indicator: "orange"
                    });
                }
            },
        });
    },
});
