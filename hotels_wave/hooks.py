app_name = "hotels_wave"
app_title = "Hotels Wave"
app_publisher = "Mahmoud Soliman"
app_description = "A Hotels Wave Manegment App"
app_email = "mhmoud.soliman100@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "hotels_wave",
# 		"logo": "/assets/hotels_wave/logo.png",
# 		"title": "Hotels Wave",
# 		"route": "/hotels_wave",
# 		"has_permission": "hotels_wave.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/hotels_wave/css/hotels_wave.css"
# app_include_js = "/assets/hotels_wave/js/hotels_wave.js"

# include js, css files in header of web template
# web_include_css = "/assets/hotels_wave/css/hotels_wave.css"
# web_include_js = "/assets/hotels_wave/js/hotels_wave.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "hotels_wave/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Customer": "public/js/customer.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "hotels_wave/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "hotels_wave.utils.jinja_methods",
# 	"filters": "hotels_wave.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "hotels_wave.install.before_install"
# after_install = "hotels_wave.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "hotels_wave.uninstall.before_uninstall"
# after_uninstall = "hotels_wave.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "hotels_wave.utils.before_app_install"
# after_app_install = "hotels_wave.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "hotels_wave.utils.before_app_uninstall"
# after_app_uninstall = "hotels_wave.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "hotels_wave.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"on_update": "hotels_wave.hotels_wave.doctype.financial_settlement.financial_settlement.update_settlement_invoice_status",
		"on_submit": "hotels_wave.hotels_wave.doctype.financial_settlement.financial_settlement.update_settlement_invoice_status",
		"on_cancel": "hotels_wave.hotels_wave.doctype.financial_settlement.financial_settlement.update_settlement_invoice_status",
		"on_update_after_submit": "hotels_wave.hotels_wave.doctype.financial_settlement.financial_settlement.update_settlement_invoice_status",
	},
	"Payment Entry": {
		"on_submit": "hotels_wave.hotels_wave.doctype.financial_settlement.financial_settlement.update_settlement_on_payment",
		"on_cancel": "hotels_wave.hotels_wave.doctype.financial_settlement.financial_settlement.update_settlement_on_payment",
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"hourly": [
		"hotels_wave.hotels_wave.doctype.booking_intake.booking_intake.auto_confirm_bookings"
	],
	"daily": [
		"hotels_wave.hotels_wave.utils.overbooking_engine.refresh_all_overbooking_statuses"
	],
}

# Testing
# -------

# before_tests = "hotels_wave.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "hotels_wave.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "hotels_wave.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["hotels_wave.utils.before_request"]
# after_request = ["hotels_wave.utils.after_request"]

# Job Events
# ----------
# before_job = ["hotels_wave.utils.before_job"]
# after_job = ["hotels_wave.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"hotels_wave.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    {
        "dt": "Custom Field",
        "filters": {
            "name": [
                "in",
                [
                    "Customer-custom_is_hotel_entity",
                    "Customer-custom_management_company",
                    "Customer-custom_hotel",
                    "Customer-custom_hotel_name",
                    "Customer-custom_location",
                    "Customer-custom_city",
                    "Customer-custom_column_break_1",
                    "Customer-custom_section_break_contract",
                    "Customer-custom_contract_start",
                    "Customer-custom_contract_end",
                    "Customer-custom_column_break_2",
                    "Customer-custom_base_commission",
                    "Customer-custom_hotel_status",
                    "Customer-custom_hotel_type",

                    "Contract-custom_commission_calculation_method",
                    "Contract-custom_service_scope"
                ],
            ]
        }
    }
]