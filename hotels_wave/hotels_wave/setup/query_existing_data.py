"""
Query existing data from the hotels_wave system.
Run: bench --site hotels.site execute hotels_wave.hotels_wave.setup.query_existing_data.run
"""
import frappe

def run():
    print("=== Hotel Unit Types ===")
    huts = frappe.get_all("Hotel Unit Type", fields=["name", "hotel"])
    for h in huts:
        print(f"  {h.name}  hotel={h.hotel}")
        details = frappe.get_all("Hotel Unit Detail", filters={"parent": h.name},
                                  fields=["unit_type_ref", "total_units", "units_allowed_on_platforms", "overbooked"])
        for d in details:
            print(f"    - {d.unit_type_ref}: total={d.total_units} allowed={d.units_allowed_on_platforms} overbooked={d.overbooked}")

    print("\n=== OTA Account Setup ===")
    otas = frappe.get_all("OTA Account Setup", fields=["name", "hotel", "ota_name", "no_show_rate_weekday", "no_show_rate_weekend"])
    for o in otas:
        print(f"  {o.name}  hotel={o.hotel}  ota_name={o.ota_name}  ns_wd={o.no_show_rate_weekday} ns_we={o.no_show_rate_weekend}")

    print("\n=== Hotel Pricing Config ===")
    configs = frappe.get_all("Hotel Pricing Config", fields=["name", "hotel", "is_active", "safety_buffer_rate", "lock_threshold_pct"])
    for c in configs:
        print(f"  {c.name}  hotel={c.hotel}  active={c.is_active}  buffer={c.safety_buffer_rate}  lock={c.lock_threshold_pct}")

    print("\n=== Booking Intake (recent) ===")
    bookings = frappe.get_all("Booking Intake", fields=["name", "hotel", "check_in", "check_out", "booking_status", "ota_source"], order_by="creation desc", limit=10)
    for b in bookings:
        print(f"  {b.name}  hotel={b.hotel}  {b.check_in}→{b.check_out}  status={b.booking_status}  ota={b.ota_source}")

    print("\n=== Hotel Reservation (all) ===")
    reservations = frappe.get_all("Hotel Reservation", fields=["name", "hotel", "unit_type", "status", "check_in", "check_out", "number_of_rooms", "booking_source"])
    for r in reservations:
        print(f"  {r.name}  {r.hotel}  {r.unit_type}  {r.status}  {r.check_in}→{r.check_out}  rooms={r.number_of_rooms}  src={r.booking_source}")

    print("\n=== Hotel Season ===")
    seasons = frappe.get_all("Hotel Season", fields=["name", "hotel", "start_date", "end_date", "season_factor"])
    for s in seasons:
        print(f"  {s.name}  hotel={s.hotel}  {s.start_date}→{s.end_date}  factor={s.season_factor}")
