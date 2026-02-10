# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ManagementCompany(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company_name: DF.Data
		default_currency: DF.Link | None
		tax_id: DF.Data | None
	# end: auto-generated types

	pass
