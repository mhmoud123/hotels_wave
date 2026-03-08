// Copyright (c) 2026, Mahmoud Soliman and contributors
// For license information, please see license.txt

// Hotel Unit Type manages room counts only.
// Pricing (markup % and suggested base price) lives in Hotel Pricing Config.

frappe.ui.form.on("Hotel Unit Type", {
    refresh(frm) {
        // Highlight rows where overbooked > 0
        if (frm.doc.units_list) {
            frm.doc.units_list.forEach(function (row) {
                if (row.overbooked && row.overbooked > 0) {
                    const grid_row = frm.fields_dict.units_list.grid.grid_rows_by_docname[row.name];
                    if (grid_row && grid_row.row) {
                        $(grid_row.row).css({
                            "background-color": "#ffcccc",
                            "border-left": "3px solid #d32f2f",
                        });
                    }
                }
            });
        }
    },
});
