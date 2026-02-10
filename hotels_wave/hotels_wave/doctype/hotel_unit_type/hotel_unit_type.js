// Copyright (c) 2026, Mahmoud Soliman and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hotel Unit Type", {
    refresh(frm) {
        // Highlight rows in red where overbooked > 0
        frm.fields_dict.units_list.$wrapper
            .find(".rows .frappe-control[data-fieldname='units_list'] .rows .row")
            .each(function () {
                // fallback: iterate grid rows
            });

        if (frm.doc.units_list) {
            frm.doc.units_list.forEach(function (row) {
                if (row.overbooked && row.overbooked > 0) {
                    // Apply red background to the grid row
                    let grid_row = frm.fields_dict.units_list.grid.grid_rows_by_docname[row.name];
                    if (grid_row && grid_row.row) {
                        $(grid_row.row).css({
                            "background-color": "#ffcccc",
                            "border-left": "3px solid #d32f2f"
                        });
                    }
                }
            });
        }
    },
});
