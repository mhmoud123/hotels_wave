// Copyright (c) 2026, Mahmoud Soliman and contributors
// For license information, please see license.txt

// cost_per_night and suggested_price are read-only fields computed server-side
// in HotelPricingConfig.validate() from the Hotel Cost Structure.
// The only thing the admin edits here is markup_pct per room type.
// Saving the form (or the cost structure changing) triggers the recompute automatically.

frappe.ui.form.on("Hotel Room Type Pricing", {
    markup_pct(frm) {
        // Inform the user that saving will refresh the computed prices.
        frappe.show_alert({
            message: __("Save the form to update Suggested Base Price."),
            indicator: "blue",
        });
    },
});
