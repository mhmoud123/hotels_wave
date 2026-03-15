# Copyright (c) 2026, Mahmoud Soliman and contributors
# For license information, please see license.txt

"""
Dynamic Pricing Engine for Hotels Wave.

Calculates a multi-factor dynamic price given a hotel, unit type, dates,
channel, pricing plan, customer segment and booking volume.

Formula (matches Excel DailyCalendar):
    composite_factor = product(season, dow, lead_time, los, segment,
                               occ_yield, rooms_volume)
    suggested_price  = base_price × composite_factor × demand_pressure
    final_price      = suggested_price
        × (1 - booking_volume_discount%)
        × (1 - (plan_discount% + channel_discount%))
    Note: channel commission is NOT deducted — it's the OTA's cut from hotel
    revenue, not a reduction in the guest-facing selling price.
"""

import math
from datetime import date

import frappe
from frappe.utils import getdate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_dynamic_price(
    hotel,
    unit_type,
    check_in,
    check_out,
    ota_source=None,
    pricing_plan=None,
    customer_segment=None,
    units_in_booking=1,
    booking_date=None,
    skip_lead_time=False,
):
    """
    Return a dict with:
        base_price, composite_factor, suggested_price, final_price,
        factor_breakdown, overbooking_status
    """
    check_in = getdate(check_in)
    check_out = getdate(check_out)
    if booking_date:
        booking_date = getdate(booking_date)

    config = _get_pricing_config(hotel)

    # --- Base price ---
    base_price = _get_base_price(hotel, unit_type, check_in, config)
    if not base_price:
        return _empty_result("No base price configured for this unit type.")

    # --- Individual factors ---
    occ_factor = _get_occupancy_factor(hotel, unit_type, check_in, ota_source)
    season_factor = _get_season_factor(hotel, check_in)
    dow_factor = _get_day_of_week_factor(check_in)
    lt_factor = 1.0 if skip_lead_time else _get_lead_time_factor(check_in, booking_date)
    seg_factor = _get_customer_segment_factor(customer_segment)
    los_nights = (check_out - check_in).days or 1
    los_factor = _get_length_of_stay_factor(los_nights)

    # --- Composite factor: simple product of all factors (matches Excel) ---
    factors = [occ_factor, season_factor, dow_factor, lt_factor, seg_factor, los_factor]
    composite_factor = math.prod(factors)

    # --- Demand pressure factor (scarcity / overbooking uplift) ---
    demand_pressure = _get_demand_pressure_factor(hotel, unit_type, check_in, ota_source, config)

    # --- Channel deductions ---
    channel_commission = 0.0
    channel_discount = 0.0
    if ota_source:
        ota = frappe.db.get_value(
            "OTA Account Setup",
            ota_source,
            ["platform_commission", "channel_discount_pct"],
            as_dict=True,
        )
        if ota:
            channel_commission = (ota.platform_commission or 0) / 100
            channel_discount = (ota.channel_discount_pct or 0) / 100

    # --- Plan discount (with min-stay validation) ---
    plan_discount = 0.0
    if pricing_plan:
        plan = frappe.db.get_value(
            "Pricing Plan", pricing_plan,
            ["discount_pct", "min_stay_nights"], as_dict=True,
        )
        if plan:
            if plan.min_stay_nights and los_nights < plan.min_stay_nights:
                plan_discount = 0.0  # LOS too short for this plan
            else:
                plan_discount = (plan.discount_pct or 0) / 100

    # --- Volume discount (RoomsDisc in Excel) ---
    vol_discount_raw = _range_lookup(
        "Booking Volume Discount", "min_rooms", "max_rooms", units_in_booking, value_field="discount_pct"
    )
    # _range_lookup returns 1.0 as default (designed for factors); for discounts, default is 0
    vol_discount = 0.0 if vol_discount_raw == 1.0 else (vol_discount_raw or 0) / 100

    # --- Composite price (matches Excel DailyCalendar) ---
    # Excel: base × factors × demand × (1 - RoomsDisc) × (1 - (PlanDisc + ChanDisc))
    # Channel commission is NOT deducted from selling price (it's the OTA's cut from revenue).
    suggested_price = base_price * composite_factor * demand_pressure
    final_price = (
        suggested_price
        * (1 - vol_discount)
        * (1 - (plan_discount + channel_discount))
    )

    # --- Overbooking status ---
    from hotels_wave.hotels_wave.utils.overbooking_engine import get_overbooking_status
    ob_status = get_overbooking_status(hotel, unit_type, check_in, ota_source)

    lead_time_days = (check_in - (booking_date or date.today())).days

    factor_breakdown = {
        "occupancy": occ_factor,
        "seasonality": season_factor,
        "day_of_week": dow_factor,
        "lead_time": lt_factor,
        "customer_segment": seg_factor,
        "length_of_stay": los_factor,
        "demand_pressure": demand_pressure,
        "channel_commission_pct": channel_commission * 100,
        "channel_discount_pct": channel_discount * 100,
        "plan_discount_pct": plan_discount * 100,
        "volume_discount_pct": vol_discount * 100,
    }

    return {
        "base_price": base_price,
        "composite_factor": composite_factor,
        "demand_pressure": demand_pressure,
        "suggested_price": suggested_price,
        "final_price": final_price,
        "factor_breakdown": factor_breakdown,
        "overbooking_status": ob_status,
        "length_of_stay_nights": los_nights,
        "lead_time_days": lead_time_days,
    }


# ---------------------------------------------------------------------------
# Helper: base price lookup (priority order)
# ---------------------------------------------------------------------------

def _get_base_price(hotel, unit_type, check_in, config):
    """
    Base price priority:

    1. Hotel Pricing Config → room_type_pricing → suggested_price
       (auto-computed: cost_per_night × (1 + markup_pct / 100))
       This is the primary source.  Admin only sets markup_pct.

    2. Season Unit Rates for check_in date
       Fallback for hotels that prefer explicit season-level price overrides
       instead of the factor-based system.
    """
    # 1. Hotel Pricing Config → suggested_price (cost-derived, read-only)
    if config:
        config_doc = frappe.get_doc("Hotel Pricing Config", config)
        for row in config_doc.room_type_pricing or []:
            if row.unit_type == unit_type and row.suggested_price:
                return float(row.suggested_price)

    # 2. Season Unit Rates fallback
    season = _get_active_season(hotel, check_in)
    if season:
        price = frappe.db.get_value(
            "Season Unit Rates",
            {"parent": season, "unit_type": unit_type},
            "price",
        )
        if price:
            return float(price)

    return None


# ---------------------------------------------------------------------------
# Helper: factor lookups
# ---------------------------------------------------------------------------

def _range_lookup(doctype, min_field, max_field, value, value_field="factor"):
    """
    Generic range lookup — returns the value_field for the matching range row.
    If value exceeds all ranges, returns the factor from the highest range
    (matches Excel LOOKUP approximate-match behavior).
    """
    rows = frappe.get_all(
        doctype,
        fields=[min_field, max_field, value_field],
        order_by=f"{max_field} asc",
    )
    best = None
    for row in rows:
        if row[min_field] <= value <= row[max_field]:
            return float(row[value_field]) if row[value_field] is not None else 1.0
        # Track the highest range in case value exceeds all
        if best is None or row[max_field] > best[max_field]:
            best = row
    # Value exceeds all ranges — clamp to the highest range's factor
    if best and value > best[max_field]:
        return float(best[value_field]) if best[value_field] is not None else 1.0
    return 1.0


def _get_occupancy_factor(hotel, unit_type, check_in, ota_source=None):
    """Look up occupancy yield factor using expected occupied / sellable from overbooking engine."""
    from hotels_wave.hotels_wave.utils.overbooking_engine import get_overbooking_status

    ob = get_overbooking_status(hotel, unit_type, check_in, ota_source)
    exp_occ_pct = ob.get("exp_occ_for_pricing", 0) * 100

    return _range_lookup("Occupancy Yield Factor", "min_occupancy_pct", "max_occupancy_pct", exp_occ_pct)


def _get_season_factor(hotel, check_in):
    season = _get_active_season(hotel, check_in)
    if not season:
        return 1.0
    factor = frappe.db.get_value("Hotel Season", season, "season_factor")
    return float(factor or 1.0)


def _get_active_season(hotel, check_date):
    seasons = frappe.get_all(
        "Hotel Season",
        filters={"hotel": hotel, "start_date": ["<=", check_date], "end_date": [">=", check_date]},
        fields=["name"],
        limit=1,
    )
    return seasons[0].name if seasons else None


def _get_day_of_week_factor(check_in):
    day_name = check_in.strftime("%A")  # e.g. "Monday"
    factor = frappe.db.get_value("Day Of Week Factor", day_name, "factor")
    return float(factor or 1.0)


def _get_lead_time_factor(check_in, booking_date=None):
    """Lead Time = check_in - booking_date (or today if not provided)."""
    reference_date = booking_date or date.today()
    days_ahead = (check_in - reference_date).days
    if days_ahead < 0:
        days_ahead = 0
    return _range_lookup("Lead Time Factor", "min_days", "max_days", days_ahead)


def _get_customer_segment_factor(segment):
    if not segment:
        return 1.0
    factor = frappe.db.get_value("Customer Segment Factor", segment, "factor")
    return float(factor or 1.0)


def _get_length_of_stay_factor(nights):
    return _range_lookup("Length Of Stay Factor", "min_nights", "max_nights", nights)


def _get_rooms_volume_factor(hotel, unit_type, check_in, units_in_booking):
    """Express units_in_booking as % of total_units, then look up factor."""
    hotel_unit_type = frappe.db.get_value("Hotel Unit Type", {"hotel": hotel}, "name")
    if not hotel_unit_type:
        return 1.0
    total = frappe.db.get_value(
        "Hotel Unit Detail",
        {"parent": hotel_unit_type, "unit_type_ref": unit_type},
        "total_units",
    ) or 1
    pct = min(100.0, (units_in_booking / total) * 100)
    return _range_lookup("Rooms Volume Factor", "min_pct", "max_pct", pct)


# ---------------------------------------------------------------------------
# Helper: demand pressure (scarcity uplift)
# ---------------------------------------------------------------------------

def _get_demand_pressure_factor(hotel, unit_type, check_in, ota_source, config_name):
    """
    Tiered price uplift matching Excel DailyCalendar formula:

        IF Booked > Sellable        → 1.25
        ELIF ExpOcc >= MinOcc (20%) → 1.15
        ELIF ExpOcc >= 0.9          → 1.07
        ELSE                        → 1.0

    ExpOcc = Expected Occupied / Sellable Rooms (not Physical).
    MinOcc defaults to 20% (Excel InputsControl!B8).
    """
    from hotels_wave.hotels_wave.utils.overbooking_engine import get_overbooking_status

    ob = get_overbooking_status(hotel, unit_type, check_in, ota_source)
    booked = ob.get("booked_rooms", 0)
    sellable = ob.get("sellable_rooms", 0)
    expected = ob.get("expected_occupied", 0)
    exp_occ = expected / sellable if sellable else 0

    min_occ = 0.2  # Excel default (InputsControl!B8)

    if booked > sellable:
        return 1.25
    elif exp_occ >= min_occ:
        return 1.15
    elif exp_occ >= 0.9:
        return 1.07
    else:
        return 1.0


# ---------------------------------------------------------------------------
# Helper: profit floor (with alpha interpolation for fixed costs)
# ---------------------------------------------------------------------------

def _apply_profit_floor(hotel, unit_type, price, nights, config_name):
    if not config_name:
        return price

    config = frappe.get_doc("Hotel Pricing Config", config_name)
    min_margin = (config.min_margin_pct or 0) / 100
    min_per_night = config.min_profit_per_night or 0

    # Cost per night with alpha interpolation
    cost_per_night = _get_cost_per_night(hotel, unit_type)

    floor_from_margin = cost_per_night * (1 + min_margin) if cost_per_night else 0
    floor_from_config = float(min_per_night) + cost_per_night if cost_per_night else float(min_per_night)
    floor = max(floor_from_margin, floor_from_config)

    if floor and price < floor:
        return floor
    return price



def _get_cost_per_night(hotel, unit_type):
    """
    Return the total cost per room per night for this unit_type.

    Uses alpha interpolation for fixed costs:
        CPARN = fixed_cost / (rooms × days)           — full capacity assumption
        CPORN = fixed_cost / (rooms × days × occ)     — actual occupancy
        Alpha = clamp((occ - min_occ) / (1 - min_occ), 0, 1)
        final_fixed = Alpha × CPORN + (1 - Alpha) × CPARN

    Variable costs are added as-is (already per-room-per-night).
    """
    cost_doc_name = frappe.db.get_value(
        "Hotel Cost Structure", {"hotel": hotel}, "name", order_by="effective_date desc"
    )
    if not cost_doc_name:
        return 0.0

    cost_doc = frappe.get_doc("Hotel Cost Structure", cost_doc_name)

    # Separate fixed and variable cost components
    fixed_cparn = 0.0
    variable_total = 0.0
    for item in cost_doc.cost_items or []:
        if item.unit_type and item.unit_type != unit_type:
            continue
        cpn = float(item.cost_per_room_per_night or 0)
        if item.cost_type == "Variable":
            variable_total += cpn
        else:
            fixed_cparn += cpn

    if not fixed_cparn:
        return fixed_cparn + variable_total

    # Get current occupancy for alpha interpolation
    occ = _get_current_occupancy_ratio(hotel, unit_type)
    min_occ = 0.60  # min_occupancy_pct not yet a DocType field — fixed default

    if occ <= 0:
        occ = min_occ  # avoid division by zero, assume min

    # Alpha interpolation
    fixed_cporn = fixed_cparn / occ if occ > 0 else fixed_cparn
    if min_occ >= 1.0:
        alpha = 1.0
    else:
        alpha = max(0.0, min(1.0, (occ - min_occ) / (1.0 - min_occ)))

    final_fixed = alpha * fixed_cporn + (1 - alpha) * fixed_cparn
    return final_fixed + variable_total


def _get_current_occupancy_ratio(hotel, unit_type):
    """Return the current occupancy as a ratio (0.0 - 1.0) from Hotel Unit Detail snapshot."""
    hotel_unit_type = frappe.db.get_value("Hotel Unit Type", {"hotel": hotel}, "name")
    if not hotel_unit_type:
        return 0.0

    detail = frappe.db.get_value(
        "Hotel Unit Detail",
        {"parent": hotel_unit_type, "unit_type_ref": unit_type},
        ["total_units", "units_allowed_on_platforms", "overbooked"],
        as_dict=True,
    )
    if not detail or not detail.total_units:
        return 0.0

    booked = (detail.total_units - (detail.units_allowed_on_platforms or 0)) + (detail.overbooked or 0)
    return min(1.0, booked / detail.total_units)


# ---------------------------------------------------------------------------
# Helper: config lookup
# ---------------------------------------------------------------------------

def _get_pricing_config(hotel):
    return frappe.db.get_value(
        "Hotel Pricing Config", {"hotel": hotel, "is_active": 1}, "name"
    )


def _empty_result(reason=""):
    return {
        "base_price": 0,
        "composite_factor": 1.0,
        "demand_pressure": 1.0,
        "suggested_price": 0,
        "final_price": 0,
        "factor_breakdown": {},
        "overbooking_status": {},
        "length_of_stay_nights": 0,
        "lead_time_days": 0,
        "error": reason,
    }
