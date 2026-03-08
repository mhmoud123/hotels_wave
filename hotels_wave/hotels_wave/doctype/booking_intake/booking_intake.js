// Copyright (c) 2026, Mahmoud Soliman and contributors
// For license information, please see license.txt

// ─────────────────────────────────────────────────────────────────────────────
// Parent form triggers
// ─────────────────────────────────────────────────────────────────────────────
frappe.ui.form.on("Booking Intake", {

    refresh(frm) {
        frm.trigger("refresh_pricing");

        // Add "Create Reservation" button for confirmed bookings
        if (frm.doc.docstatus === 1 && frm.doc.booking_status === "Confirmed") {
            frm.add_custom_button(__("Create Reservation"), () => {
                frappe.call({
                    method: "hotels_wave.hotels_wave.doctype.booking_intake.booking_intake.create_reservation_from_booking",
                    args: { booking_name: frm.doc.name },
                    callback(r) {
                        if (!r.exc) frm.reload_doc();
                    },
                });
            }, __("Actions"));
        }
    },

    // Any parent-level field that affects pricing
    check_in: (frm) => frm.trigger("refresh_pricing"),
    check_out: (frm) => frm.trigger("refresh_pricing"),
    ota_source: (frm) => frm.trigger("refresh_pricing"),
    pricing_plan: (frm) => frm.trigger("refresh_pricing"),
    customer_segment: (frm) => frm.trigger("refresh_pricing"),

    refresh_pricing(frm) {
        const { hotel, check_in, check_out, ota_source, pricing_plan, customer_segment } = frm.doc;

        // Need at minimum hotel + dates to price
        if (!hotel || !check_in || !check_out) return;

        // Build the availability_rows list from the child table
        const availability_rows = (frm.doc.availability_control || [])
            .filter(r => r.unit_type && r.allocated_units > 0)
            .map(r => ({ unit_type: r.unit_type, allocated_units: r.allocated_units }));

        if (!availability_rows.length) {
            // Nothing to price yet — clear pricing fields
            frm.set_value("computed_base_price", 0);
            frm.set_value("suggested_price", 0);
            frm.set_value("applied_price_factor", 1.0);
            frm.dashboard.clear_headline();
            return;
        }

        frappe.call({
            method: "hotels_wave.hotels_wave.api.pricing.get_booking_pricing",
            args: {
                hotel,
                check_in,
                check_out,
                availability_rows: JSON.stringify(availability_rows),
                ota_source: ota_source || null,
                pricing_plan: pricing_plan || null,
                customer_segment: customer_segment || null,
            },
            callback(r) {
                if (r.exc || !r.message) return;
                const d = r.message;
                const p = frappe.boot.sysdefaults.float_precision || 6;

                if (flt(frm.doc.computed_base_price, p) !== flt(d.total_base_price, p)) {
                    frm.set_value("computed_base_price", d.total_base_price || 0);
                }
                if (flt(frm.doc.suggested_price, p) !== flt(d.total_suggested_price, p)) {
                    frm.set_value("suggested_price", d.total_suggested_price || 0);
                }
                if (flt(frm.doc.applied_price_factor, p) !== flt(d.composite_factor, p)) {
                    frm.set_value("applied_price_factor", d.composite_factor || 1.0);
                }
                if (flt(frm.doc.lead_time_days) !== flt(d.lead_time_days)) {
                    frm.set_value("lead_time_days", d.lead_time_days || 0);
                }
                if (flt(frm.doc.length_of_stay_nights) !== flt(d.length_of_stay_nights)) {
                    frm.set_value("length_of_stay_nights", d.length_of_stay_nights || 0);
                }

                // Call helpers directly — frm.trigger() does not forward extra args
                _show_overbooking_indicator(frm, d.worst_overbooking);
                _show_row_pricing_summary(frm, d.rows);
            },
        });
    },

});

// ─────────────────────────────────────────────────────────────────────────────
// Availability Control child table triggers
// Any change inside the child table re-prices the whole booking
// ─────────────────────────────────────────────────────────────────────────────
frappe.ui.form.on("Availability Control", {
    unit_type(frm) { frm.trigger("refresh_pricing"); },
    allocated_units(frm) { frm.trigger("refresh_pricing"); },
    availability_control_remove(frm) { frm.trigger("refresh_pricing"); },
});

// ─────────────────────────────────────────────────────────────────────────────
// Internal helpers
// ─────────────────────────────────────────────────────────────────────────────

function _show_overbooking_indicator(frm, ob) {
    // `ob` comes directly from the API response (worst_overbooking)
    if (ob && ob.risk_level) {
        _render_ob_headline(frm, ob);
        return;
    }

    // Fallback: fetch for the first unit type if no ob data passed
    const firstRow = (frm.doc.availability_control || []).find(r => r.unit_type);
    if (!firstRow || !frm.doc.hotel || !frm.doc.check_in) {
        frm.dashboard.clear_headline();
        return;
    }

    frappe.call({
        method: "hotels_wave.hotels_wave.api.pricing.get_overbooking_status_for_date",
        args: {
            hotel: frm.doc.hotel,
            unit_type: firstRow.unit_type,
            check_in: frm.doc.check_in,
            ota_source: frm.doc.ota_source || null,
        },
        callback(r) {
            if (!r.exc && r.message) _render_ob_headline(frm, r.message);
        },
    });
}

function _show_row_pricing_summary(frm, rows) {
    if (!rows || !rows.length) return;

    const lines = rows.map(row => {
        const nights = frm.doc.length_of_stay_nights || 1;
        return `<tr>
            <td style="padding:2px 8px">${row.unit_type}</td>
            <td style="padding:2px 8px;text-align:right">${row.allocated_units}</td>
            <td style="padding:2px 8px;text-align:right">${nights}</td>
            <td style="padding:2px 8px;text-align:right">${format_currency(row.base_price, frm.doc.currency)}/night (suggested)</td>
            <td style="padding:2px 8px;text-align:right;font-weight:bold">
                ${format_currency(row.line_total, frm.doc.currency)}
            </td>
            <td style="padding:2px 8px;text-align:center">
                ${_ob_badge(row.overbooking)}
            </td>
        </tr>`;
    }).join("");

    const html = `
        <table style="width:100%;font-size:12px;border-collapse:collapse;margin-top:4px">
            <thead>
                <tr style="background:#f4f5f6;color:#6c7680">
                    <th style="padding:4px 8px;text-align:left">Unit Type</th>
                    <th style="padding:4px 8px;text-align:right">Rooms</th>
                    <th style="padding:4px 8px;text-align:right">Nights</th>
                    <th style="padding:4px 8px;text-align:right">Base/Night</th>
                    <th style="padding:4px 8px;text-align:right">Line Total</th>
                    <th style="padding:4px 8px;text-align:center">Risk</th>
                </tr>
            </thead>
            <tbody>${lines}</tbody>
        </table>`;

    // Render inside the pricing section
    const pricingSection = frm.get_field("section_break_pricing");
    if (!pricingSection || !pricingSection.$wrapper) return;

    pricingSection.$wrapper.find(".pricing-breakdown").remove();
    pricingSection.$wrapper
        .find(".section-body")
        .append(`<div class="pricing-breakdown" style="margin:8px 0">${html}</div>`);
}

function _render_ob_headline(frm, ob) {
    const risk = ob.risk_level || "LOW";
    const lock = ob.lock_status === "LOCK" ? " 🔒 LOCKED" : "";
    const color = risk === "HIGH" ? "#e74c3c" : risk === "MEDIUM" ? "#e67e22" : "#27ae60";
    frm.dashboard.set_headline(
        `<span style="color:${color};font-weight:bold;">
            Overbooking Risk: ${risk}${lock} &nbsp;|&nbsp;
            Occupancy: ${ob.adj_occupancy_pct || 0}% &nbsp;|&nbsp;
            Sellable: ${ob.sellable_rooms || 0} &nbsp;|&nbsp;
            Booked: ${ob.booked_rooms || 0}
        </span>`
    );
}

function _ob_badge(ob) {
    if (!ob || !ob.risk_level) return "";
    const color = ob.risk_level === "HIGH" ? "#e74c3c" : ob.risk_level === "MEDIUM" ? "#e67e22" : "#27ae60";
    return `<span style="background:${color};color:#fff;padding:1px 6px;border-radius:3px;font-size:11px">
                ${ob.risk_level}${ob.lock_status === "LOCK" ? " 🔒" : ""}
            </span>`;
}

function format_currency(amount, currency) {
    if (!amount) return "0";
    return `${currency || ""} ${format_number(amount, null, 2)}`;
}
