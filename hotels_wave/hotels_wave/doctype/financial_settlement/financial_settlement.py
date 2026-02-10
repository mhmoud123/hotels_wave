# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class FinancialSettlement(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from hotels_wave.hotels_wave.doctype.settlement_booking_detail.settlement_booking_detail import SettlementBookingDetail

		bookings: DF.Table[SettlementBookingDetail]
		hotel: DF.Link | None
		manual_discount: DF.Currency
		net_commission_due: DF.Currency
		period_end: DF.Date | None
		period_start: DF.Date | None
		sales_invoice: DF.Link | None
		sales_invoice_status: DF.Data | None
		total_gross_revenue: DF.Currency
	# end: auto-generated types

	def validate(self):
		"""Validate bookings and calculate totals on validate."""
		self.validate_no_duplicate_bookings()
		self.calculate_totals()

	def validate_no_duplicate_bookings(self):
		"""Ensure no booking in this settlement has already been settled in another submitted settlement."""
		for row in self.bookings:
			if not row.booking_ref:
				continue
			existing = frappe.db.exists(
				"Settlement Booking Detail",
				{
					"booking_ref": row.booking_ref,
					"parenttype": "Financial Settlement",
					"docstatus": 1,
					"parent": ["!=", self.name] if self.name else ["is", "set"],
				},
			)
			if existing:
				frappe.throw(
					_("Booking {0} (Row {1}) has already been settled in another Financial Settlement.").format(
						row.booking_ref, row.idx
					)
				)

	def calculate_totals(self):
		"""
		Calculate total_gross_revenue and net_commission_due.
		Uses the Commission Hierarchy: Season > OTA > Base.
		"""
		total_gross = 0
		total_commission = 0

		for row in self.bookings:
			# Get the booking document for commission calculation
			if row.booking_ref:
				booking = frappe.get_doc("Booking Intake", row.booking_ref)
				
				# Get the commission rate using the hierarchy
				commission_rate = get_commission_rate(
					hotel=self.hotel,
					ota_source=booking.ota_source,
					booking_date=booking.check_in
				)
				
				# Update the row with calculated values
				row.gross_amount = flt(booking.total_value)
				row.applied_commission_rate = flt(commission_rate)
				row.commission_amount = flt(row.gross_amount) * flt(commission_rate) / 100
				
				total_gross += flt(row.gross_amount)
				total_commission += flt(row.commission_amount)
		if total_commission > 0 and flt(self.manual_discount) > 0:
			for row in self.bookings:
				discount_share = flt(row.commission_amount) / total_commission * self.manual_discount
				row.commission_amount = flt(row.commission_amount) - discount_share
			
		# Set totals
		self.total_gross_revenue = flt(total_gross)
		self.net_commission_due = flt(total_commission) - flt(self.manual_discount or 0)

	def on_submit(self):
		"""Generate Sales Invoice on submit."""
		self.create_sales_invoice()

	def create_sales_invoice(self):
		"""
		Create a Sales Invoice for the net_commission_due.
		Uses Customer linked to the hotel via custom_hotel field.
		"""
		if not self.hotel:
			frappe.throw(_("Hotel is required to create Sales Invoice"))

		# self.hotel is now the Customer directly
		customer = self.hotel

		# Get customer/hotel details for additional info
		customer_doc = frappe.get_doc("Customer", customer)

		# Create Sales Invoice
		sales_invoice = frappe.new_doc("Sales Invoice")
		sales_invoice.customer = customer
		sales_invoice.posting_date = frappe.utils.today()
		
		# Set accounting dimension if Management Company exists
		# The Customer may have a custom_management_company field
		management_company = frappe.db.get_value("Customer", customer, "custom_management_company")
		if management_company:
			if "management_company" in sales_invoice.meta.fields:
				sales_invoice.management_company = management_company
		
		# Group bookings by OTA source: track count and sum commission amounts
		ota_data = {}
		for item in self.bookings:
			ota_source = frappe.db.get_value("Booking Intake", item.booking_ref, "ota_source")
			if ota_source not in ota_data:
				ota_data[ota_source] = {"count": 0, "total_commission": 0}
			ota_data[ota_source]["count"] += 1
			ota_data[ota_source]["total_commission"] += flt(item.commission_amount)
		
		# Create one invoice line item per OTA source with qty = booking count
		for ota_source, data in ota_data.items():
			item_ref = frappe.db.get_value("OTA Account Setup", ota_source, "ota_name")
			item_name, description = frappe.db.get_value("Item", item_ref, ["item_name", "description"])
			sales_invoice.append("items", {
				"item_code": item_ref,
				"item_name": item_name,
				"description": description,
				"qty": data["count"],
				"rate": data["total_commission"] / data["count"],
			})

		# Link back to the settlement
		sales_invoice.flags.ignore_permissions = True
		sales_invoice.insert()
		# sales_invoice.submit()

		# Store the invoice reference and status in the settlement
		self.db_set("sales_invoice", sales_invoice.name)
		self.db_set("sales_invoice_status", sales_invoice.status)

		frappe.msgprint(
			_("Sales Invoice {0} created successfully").format(
				frappe.utils.get_link_to_form("Sales Invoice", sales_invoice.name)
			),
			alert=True
		)

		return sales_invoice.name

def get_commission_rate(hotel, ota_source, booking_date):
	"""
	Commission Hierarchy Script - The Calculation Engine.
	
	Priority (Descending Order):
	1. Season Rate: Check if booking_date falls within a Hotel Season
	2. OTA Rate: Use platform_commission from OTA Account Setup
	3. Base Rate: Fallback to custom_base_commission in Customer
	
	Args:
		hotel: Customer name (Link to Customer with custom_is_hotel_entity=1)
		ota_source: OTA Account Setup name (Link)
		booking_date: Date to check for seasonal rates
	
	Returns:
		Commission percentage (float)
	"""
	# 1. Check for Seasonal Commission
	if booking_date and hotel:
		seasonal_commission = frappe.db.get_value(
			"Hotel Season",
			{
				"hotel": hotel,
				"start_date": ["<=", booking_date],
				"end_date": [">=", booking_date],
			},
			"seasonal_commission"
		)
		
		if seasonal_commission:
			return flt(seasonal_commission)

	# 2. Check OTA Platform Commission
	if ota_source:
		platform_commission = frappe.db.get_value(
			"OTA Account Setup",
			ota_source,
			"platform_commission"
		)
		
		if platform_commission:
			return flt(platform_commission)

	# 3. Fallback to Base Commission from Customer (custom field)
	if hotel:
		base_commission = frappe.db.get_value(
			"Customer",
			hotel,
			"custom_base_commission"
		)
		
		if base_commission:
			return flt(base_commission)

	# Default to 0 if nothing found
	return 0


@frappe.whitelist()
def get_confirmed_bookings(hotel, period_start, period_end):
	"""
	Fetch confirmed bookings for the selected hotel and period.
	Used by the 'Fetch Confirmed Bookings' button.
	
	Args:
		hotel: Customer name (Link to Customer with custom_is_hotel_entity=1)
		period_start: Start date of the period
		period_end: End date of the period
	
	Returns:
		List of booking details suitable for the child table
	"""
	if not hotel or not period_start or not period_end:
		frappe.throw(_("Hotel, Period Start, and Period End are required"))

	# Get bookings that are already settled (in submitted Financial Settlements only)
	already_settled = frappe.get_all(
		"Settlement Booking Detail",
		filters={"parenttype": "Financial Settlement", "docstatus": 1},
		pluck="booking_ref"
	)

	bookings = frappe.get_all(
		"Booking Intake",
		filters={
			"hotel": hotel,
			"booking_status": "Confirmed",
			"check_in": [">=", period_start],
			"check_out": ["<=", period_end],
			"docstatus": 1,
			"name": ["not in", already_settled]
		},
		fields=["name", "total_value", "ota_source", "check_in", "external_id"],
	)

	result = []
	for booking in bookings:
		commission_rate = get_commission_rate(
			hotel=hotel,
			ota_source=booking.ota_source,
			booking_date=booking.check_in
		)
		ota_item = frappe.db.get_value(
			"OTA Account Setup",
			booking.ota_source,
			"ota_name"
		)
		result.append({
			"booking_ref": booking.name,
			"booking_ota": ota_item,
			"external_id": booking.external_id,
			"gross_amount": flt(booking.total_value),
			"applied_commission_rate": flt(commission_rate),
			"commission_amount": flt(booking.total_value) * flt(commission_rate) / 100,
		})

	return result


def update_settlement_invoice_status(doc, method):
	"""
	Document event handler to update Financial Settlement when Sales Invoice status changes.
	This is called on Sales Invoice on_update, on_submit, on_cancel, and on_update_after_submit.
	
	Args:
		doc: Sales Invoice document
		method: The event method name (on_update, on_submit, etc.)
	"""
	# Find all Financial Settlements linked to this Sales Invoice
	settlements = frappe.get_all(
		"Financial Settlement",
		filters={"sales_invoice": doc.name},
		fields=["name"]
	)
	
	if not settlements:
		return
	
	# Update the status in all linked settlements
	for settlement in settlements:
		frappe.db.set_value(
			"Financial Settlement",
			settlement.name,
			"sales_invoice_status",
			doc.status,
			update_modified=False
		)


def update_settlement_on_payment(doc, method):
	"""
	Document event handler to update Financial Settlement when Payment Entry is submitted/cancelled.
	Payment Entry doesn't directly trigger Sales Invoice on_update, so we need to handle it separately.
	
	Args:
		doc: Payment Entry document
		method: The event method name (on_submit, on_cancel)
	"""
	# Get all Sales Invoices linked to this Payment Entry
	sales_invoices = []
	
	for ref in doc.references:
		if ref.reference_doctype == "Sales Invoice":
			sales_invoices.append(ref.reference_name)
	
	if not sales_invoices:
		return
	
	# For each Sales Invoice, update the linked Financial Settlement
	for invoice_name in sales_invoices:
		# Get the current status of the Sales Invoice (it should be updated by now)
		invoice_status = frappe.db.get_value("Sales Invoice", invoice_name, "status")
		
		# Find Financial Settlements linked to this invoice
		settlements = frappe.get_all(
			"Financial Settlement",
			filters={"sales_invoice": invoice_name},
			fields=["name"]
		)
		
		# Update the status in all linked settlements
		for settlement in settlements:
			frappe.db.set_value(
				"Financial Settlement",
				settlement.name,
				"sales_invoice_status",
				invoice_status,
				update_modified=False
			)

