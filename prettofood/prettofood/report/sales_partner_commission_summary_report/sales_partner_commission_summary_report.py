# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import flt


def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	data = get_entries(filters)

	return columns, data

def get_columns(filters):

	columns =[
		{
			"label": _("Sales Invoice"),
			"options": "Sales Invoice",
			"fieldname": "name",
			"fieldtype": "Link",
			"width": 120
		},
		{
			"label": _("Customer"),
			"options": "Customer",
			"fieldname": "customer",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Territory"),
			"options": "Territory",
			"fieldname": "territory",
			"fieldtype": "Link",
			"width": 100
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 110
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Outstanding"),
			"fieldname": "outstanding_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Sales Partner"),
			"options": "Sales Partner",
			"fieldname": "sales_partner",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("S.P Commission"),
			"fieldname": "sales_partner_commission",
			"fieldtype": "Currency",
			"width": 160
		},
		{
			"label": _("Sales Manager"),
			"options": "Sales Partner",
			"fieldname": "sales_manager",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("S.M Commission"),
			"fieldname": "sales_manager_commission",
			"fieldtype": "Currency",
			"width": 160
		}
	]

	return columns

def get_entries(filters):
	date_field = "posting_date"
	conditions = get_conditions(filters, date_field)
	entries = frappe.db.sql("""
		SELECT
			name, customer, territory, posting_date,grand_total, base_net_total as amount,
			sales_partner, sales_partner_commission, sales_manager, sales_manager_commission,outstanding_amount
		FROM
			`tabSales Invoice`
		WHERE
			{2} and docstatus = 1 and sales_partner is not null
			and sales_partner != '' and sales_partner_commission > 0 order by name desc, sales_partner
		""".format(date_field, filters.get('sales_invoice'), conditions), filters, as_dict=1)

	return entries

def get_conditions(filters, date_field):
	conditions = "1=1"

	for field in ["company", "customer", "territory"]:
		if filters.get(field):
			conditions += " and {0} = %({1})s".format(field, field)

	if filters.get("sales_partner"):
		conditions += " and sales_partner = %(sales_partner)s"

	if filters.get("from_date"):
		conditions += " and {0} >= %(from_date)s".format(date_field)

	if filters.get("to_date"):
		conditions += " and {0} <= %(to_date)s".format(date_field)

	if filters.get("unpaid1"):
		conditions += " and paid = 0"

	if filters.get("unpaid2"):
		conditions += " and paid2 = 0"

	return conditions