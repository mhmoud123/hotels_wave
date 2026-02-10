// Copyright (c) 2024, Mahmoud Soliman and contributors
// For license information, please see license.txt

frappe.ui.form.on("Customer", {
    refresh(frm) {
        // Only show the button if this customer has custom_is_hotel_entity checked
        // and doesn't already have hotel details filled
        if (frm.doc.custom_is_hotel_entity && !frm.doc.custom_hotel_name) {
            frm.add_custom_button(__("Setup Hotel Details"), function () {
                let dialog = new frappe.ui.Dialog({
                    title: __("Setup Hotel Details"),
                    fields: [
                        {
                            label: __("Hotel Name"),
                            fieldname: "hotel_name",
                            fieldtype: "Data",
                            reqd: 1,
                            default: frm.doc.customer_name
                        },
                        {
                            fieldtype: "Column Break"
                        },
                        {
                            label: __("Hotel Type"),
                            fieldname: "hotel_type",
                            fieldtype: "Select",
                            options: "Hotel Apartments\nResort\nRooms",
                            default: "Hotel Apartments"
                        },
                        {
                            fieldtype: "Section Break",
                            label: __("Location Details")
                        },
                        {
                            label: __("Location"),
                            fieldname: "location",
                            fieldtype: "Data"
                        },
                        {
                            fieldtype: "Column Break"
                        },
                        {
                            label: __("City"),
                            fieldname: "city",
                            fieldtype: "Data"
                        },
                        {
                            fieldtype: "Section Break",
                            label: __("Contract Details")
                        },
                        {
                            label: __("Contract Start"),
                            fieldname: "contract_start",
                            fieldtype: "Date"
                        },
                        {
                            label: __("Contract End"),
                            fieldname: "contract_end",
                            fieldtype: "Date"
                        },
                        {
                            fieldtype: "Column Break"
                        },
                        {
                            label: __("Base Commission (%)"),
                            fieldname: "base_commission",
                            fieldtype: "Percent"
                        }
                    ],
                    primary_action_label: __("Save Hotel Details"),
                    primary_action(values) {
                        // Update the Customer's custom fields directly
                        frappe.call({
                            method: "frappe.client.set_value",
                            args: {
                                doctype: "Customer",
                                name: frm.doc.name,
                                fieldname: {
                                    custom_hotel_name: values.hotel_name,
                                    custom_hotel_type: values.hotel_type,
                                    custom_location: values.location,
                                    custom_city: values.city,
                                    custom_contract_start: values.contract_start,
                                    custom_contract_end: values.contract_end,
                                    custom_base_commission: values.base_commission
                                }
                            },
                            freeze: true,
                            freeze_message: __("Saving Hotel Details..."),
                            callback: function (r) {
                                if (r.message) {
                                    dialog.hide();
                                    frappe.show_alert({
                                        message: __("Hotel details saved successfully"),
                                        indicator: "green"
                                    });
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                });

                dialog.show();
            }, __("Actions"));
        }

        // Show hotel name if details are filled
        if (frm.doc.custom_hotel_name) {
            frm.dashboard.add_indicator(
                __("Hotel: {0}", [frm.doc.custom_hotel_name]),
                "green"
            );
        }
    }
});
