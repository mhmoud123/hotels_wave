# Copyright (c) 2024, Mahmoud Soliman and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class OTAAccountSetup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		connection_type: DF.Literal["Manual", "Channel Manager"]
		hotel: DF.Link | None
		ota_id: DF.Data | None
		ota_name: DF.Link | None
		platform_commission: DF.Percent
	# end: auto-generated types

	pass
