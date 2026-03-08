# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HotelCostStructure(Document):
    def before_save(self):
        self._compute_cost_per_room_per_night()

    def after_save(self):
        """Re-trigger Hotel Pricing Config so suggested prices refresh automatically."""
        config_name = frappe.db.get_value(
            "Hotel Pricing Config", {"hotel": self.hotel, "is_active": 1}, "name"
        )
        if config_name:
            frappe.get_doc("Hotel Pricing Config", config_name).save(ignore_permissions=True)

    def _compute_cost_per_room_per_night(self):
        """
        For every cost item, compute and store cost_per_room_per_night.

        Room counts are read from Hotel Unit Type for this hotel.

        Fixed costs   → monthly_amount / (total_days × room_count)
            unit_type blank : room_count = total rooms across ALL types
            unit_type set   : room_count = rooms of that specific type only

        Variable costs → monthly_amount as-is (it is already the per-room-per-night rate)
        """
        # --- Fetch room counts from Hotel Unit Type ---
        hotel_unit_type = frappe.db.get_value(
            "Hotel Unit Type", {"hotel": self.hotel}, "name"
        )

        total_hotel_rooms = 0
        unit_type_rooms_map = {}   # unit_type_name → room count

        if hotel_unit_type:
            all_details = frappe.get_all(
                "Hotel Unit Detail",
                filters={"parent": hotel_unit_type},
                fields=["unit_type_ref", "total_units"],
            )
            for d in all_details:
                units = d.total_units or 0
                total_hotel_rooms += units
                unit_type_rooms_map[d.unit_type_ref] = units

        total_hotel_rooms = total_hotel_rooms or 1   # avoid division by zero

        # --- Compute per item ---
        for item in self.cost_items or []:
            amount = float(item.monthly_amount or 0)

            if item.cost_type == "Variable":
                # Variable cost: monthly_amount IS the per-room-per-night rate
                item.cost_per_room_per_night = amount

            else:
                # Fixed cost: distribute across rooms × days
                total_days = int(item.total_days or 30)
                if total_days <= 0:
                    total_days = 30

                if not item.unit_type:
                    # Hotel-wide: divide by all rooms
                    room_count = total_hotel_rooms
                else:
                    # Type-specific: divide by that type's room count only
                    room_count = unit_type_rooms_map.get(item.unit_type) or 1

                item.cost_per_room_per_night = amount / (total_days * room_count)
