# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class UnitType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		type_name: DF.Data
	# end: auto-generated types

	pass
