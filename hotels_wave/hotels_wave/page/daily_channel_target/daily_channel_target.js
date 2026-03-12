frappe.pages["daily-channel-target"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Daily Channel Target"),
		single_column: true,
	});

	page.channels = ["B2C", "B2B", "PMS"];
	page.dirty_cells = {};
	page.data = {};

	// --- Filters ---
	page.from_date = page.add_field({
		label: __("From Date"),
		fieldtype: "Date",
		fieldname: "from_date",
		default: frappe.datetime.get_today(),
		change: function () {
			// no auto-load
		},
	});

	page.to_date = page.add_field({
		label: __("To Date"),
		fieldtype: "Date",
		fieldname: "to_date",
		default: frappe.datetime.add_days(frappe.datetime.get_today(), 30),
		change: function () {
			// no auto-load
		},
	});

	// --- Load Data button ---
	page.add_inner_button(__("Load Data"), function () {
		load_data(page);
	});

	// --- Save (primary action) ---
	page.set_primary_action(__("Save"), function () {
		save_data(page);
	});

	// Container for the table
	page.$container = $('<div class="channel-target-container"></div>').appendTo(
		page.main
	);

	// Initial load
	frappe.after_ajax(function () {
		load_data(page);
	});
};

function load_data(page) {
	var from_date = page.fields_dict.from_date.get_value();
	var to_date = page.fields_dict.to_date.get_value();

	if (!from_date || !to_date) {
		frappe.msgprint(__("Please select both From Date and To Date."));
		return;
	}

	if (from_date > to_date) {
		frappe.msgprint(__("From Date must be before To Date."));
		return;
	}

	frappe.call({
		method:
			"hotels_wave.hotels_wave.page.daily_channel_target.daily_channel_target.get_channel_target_data",
		args: { from_date: from_date, to_date: to_date },
		freeze: true,
		freeze_message: __("Loading..."),
		callback: function (r) {
			page.data = r.message || {};
			page.dirty_cells = {};
			render_table(page, from_date, to_date);
		},
	});
}

function render_table(page, from_date, to_date) {
	var dates = get_date_range(from_date, to_date);
	var channels = page.channels;
	var day_abbr = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

	var html = '<table class="channel-target-table">';

	// --- Header ---
	html += "<thead><tr><th>" + __("Channel") + "</th>";
	dates.forEach(function (d) {
		var dt = new Date(d + "T00:00:00");
		var day_num = dt.getDate();
		var weekday = day_abbr[dt.getDay()];
		var is_weekend = dt.getDay() === 0 || dt.getDay() === 6;
		var cls = is_weekend ? ' class="weekend-col"' : "";
		html += "<th" + cls + ">" + day_num + "<br><small>" + weekday + "</small></th>";
	});
	html += "</tr></thead>";

	// --- Body ---
	html += "<tbody>";
	channels.forEach(function (ch) {
		html += "<tr><td>" + ch + "</td>";
		dates.forEach(function (d) {
			var key = ch + "-" + d;
			var val = page.data[key] !== undefined ? page.data[key] : "";
			var dt = new Date(d + "T00:00:00");
			var is_weekend = dt.getDay() === 0 || dt.getDay() === 6;
			var cls = is_weekend ? ' class="weekend-col"' : "";
			html +=
				"<td" +
				cls +
				'><input type="number" data-channel="' +
				ch +
				'" data-date="' +
				d +
				'" value="' +
				val +
				'" min="0"></td>';
		});
		html += "</tr>";
	});

	html += "</tbody></table>";

	page.$container.html(html);

	// --- Event: input change ---
	page.$container.find('input[type="number"]').on("input", function () {
		var $input = $(this);
		var ch = $input.data("channel");
		var d = $input.data("date");
		var key = ch + "-" + d;
		var new_val = parseInt($input.val(), 10) || 0;
		var orig_val = page.data[key] !== undefined ? page.data[key] : 0;

		if (new_val !== orig_val) {
			$input.addClass("dirty");
			page.dirty_cells[key] = { channel: ch, date: d, value: new_val };
		} else {
			$input.removeClass("dirty");
			delete page.dirty_cells[key];
		}
	});
}

function save_data(page) {
	var entries = Object.values(page.dirty_cells);

	if (!entries.length) {
		frappe.show_alert({
			message: __("No changes to save."),
			indicator: "blue",
		});
		return;
	}

	frappe.call({
		method:
			"hotels_wave.hotels_wave.page.daily_channel_target.daily_channel_target.save_channel_targets",
		args: { entries: JSON.stringify(entries) },
		freeze: true,
		freeze_message: __("Saving..."),
		callback: function (r) {
			if (r.message) {
				frappe.show_alert({
					message: r.message.message || __("Saved successfully."),
					indicator: "green",
				});

				// Update local data cache and clear dirty state
				entries.forEach(function (e) {
					var key = e.channel + "-" + e.date;
					page.data[key] = e.value;
				});
				page.dirty_cells = {};
				page.$container.find("input.dirty").removeClass("dirty");
			}
		},
	});
}

function get_date_range(from_date, to_date) {
	var dates = [];
	var current = from_date;

	while (current <= to_date) {
		dates.push(current);
		current = frappe.datetime.add_days(current, 1);
	}

	return dates;
}
