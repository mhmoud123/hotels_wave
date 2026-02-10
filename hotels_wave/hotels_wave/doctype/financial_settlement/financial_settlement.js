// Copyright (c) 2024, Mahmoud Soliman and contributors
// For license information, please see license.txt

frappe.ui.form.on("Financial Settlement", {
    refresh(frm) {
        // Add Fetch Confirmed Bookings button (only when not submitted)
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Fetch Confirmed Bookings"), function () {
                frm.trigger("fetch_confirmed_bookings");
            });
        }

        // Show Sales Invoice status with indicator (status syncs automatically via doc_events)
        if (frm.doc.sales_invoice) {
            // Set status indicator color based on invoice status
            let status = frm.doc.sales_invoice_status;
            let indicator_color = "orange";
            if (status === "Paid") {
                indicator_color = "green";
            } else if (status === "Unpaid" || status === "Overdue") {
                indicator_color = "blue";
            } else if (status === "Cancelled") {
                indicator_color = "red";
            }

            if (status) {
                frm.dashboard.set_headline(
                    __("Sales Invoice Status: <span class='indicator-pill {0}'>{1}</span>",
                        [indicator_color, status])
                );
            }
        }
    },

    fetch_confirmed_bookings(frm) {
        // Validate required fields
        if (!frm.doc.hotel) {
            frappe.msgprint(__("Please select a Hotel first"));
            return;
        }
        if (!frm.doc.period_start || !frm.doc.period_end) {
            frappe.msgprint(__("Please select Period Start and Period End dates"));
            return;
        }

        frappe.call({
            method: "hotels_wave.hotels_wave.doctype.financial_settlement.financial_settlement.get_confirmed_bookings",
            args: {
                hotel: frm.doc.hotel,
                period_start: frm.doc.period_start,
                period_end: frm.doc.period_end,
            },
            freeze: true,
            freeze_message: __("Fetching bookings..."),
            callback: function (r) {
                if (r.message) {
                    // Clear existing rows
                    frm.clear_table("bookings");

                    // Add fetched bookings
                    r.message.forEach(function (booking) {
                        let row = frm.add_child("bookings");
                        row.booking_ref = booking.booking_ref;
                        row.booking_ota = booking.booking_ota;
                        row.external_id = booking.external_id;
                        row.gross_amount = booking.gross_amount;
                        row.applied_commission_rate = booking.applied_commission_rate;
                        row.commission_amount = booking.commission_amount;
                    });

                    frm.refresh_field("bookings");

                    // Trigger recalculation
                    frm.trigger("calculate_totals");

                    frappe.msgprint({
                        title: __("Bookings Fetched"),
                        message: __("{0} confirmed booking(s) found", [r.message.length]),
                        indicator: "green",
                    });
                } else {
                    frappe.msgprint({
                        title: __("No Bookings Found"),
                        message: __("No confirmed bookings found for the selected hotel and period"),
                        indicator: "orange",
                    });
                }
            },
        });
    },

    calculate_totals(frm) {
        let total_gross = 0;
        let total_commission_before_discount = 0;

        // First pass: calculate totals using original commission amounts
        frm.doc.bookings.forEach(function (row) {
            total_gross += flt(row.gross_amount);
            // Calculate original commission from rate if available
            let original_commission = flt(row.gross_amount) * flt(row.applied_commission_rate) / 100;
            total_commission_before_discount += original_commission;
        });

        let manual_discount = flt(frm.doc.manual_discount || 0);
        let net_commission = total_commission_before_discount - manual_discount;

        // Second pass: distribute discount proportionally across rows
        if (total_commission_before_discount > 0 && manual_discount > 0) {
            frm.doc.bookings.forEach(function (row) {
                let original_commission = flt(row.gross_amount) * flt(row.applied_commission_rate) / 100;
                // Proportionally reduce each row's commission
                let discount_share = (original_commission / total_commission_before_discount) * manual_discount;
                row.commission_amount = original_commission - discount_share;
            });
            frm.refresh_field("bookings");
        } else if (manual_discount === 0) {
            // Reset to original commission amounts when no discount
            frm.doc.bookings.forEach(function (row) {
                row.commission_amount = flt(row.gross_amount) * flt(row.applied_commission_rate) / 100;
            });
            frm.refresh_field("bookings");
        }

        frm.set_value("total_gross_revenue", total_gross);
        frm.set_value("net_commission_due", net_commission);
    },

    manual_discount(frm) {
        // Recalculate net commission when manual discount changes
        frm.trigger("calculate_totals");
    },
});
