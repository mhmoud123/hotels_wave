# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HotelPricingConfig(Document):
    def validate(self):
        self._compute_suggested_prices()

    def _compute_suggested_prices(self):
        """
        For each room type row, pull cost_per_night from the Hotel Cost Structure
        and compute suggested_price = cost_per_night × (1 + markup_pct / 100).

        The admin only sets markup_pct.  Everything else is derived automatically.
        """
        from hotels_wave.hotels_wave.utils.pricing_engine import _get_cost_per_night

        for row in self.room_type_pricing or []:
            cost = _get_cost_per_night(self.hotel, row.unit_type)
            row.cost_per_night = round(cost, 4) if cost else 0.0
            markup = row.markup_pct or 0
            row.suggested_price = round(row.cost_per_night * (1 + markup / 100), 4)
