from __future__ import unicode_literals
import frappe, erpnext, json
from frappe.utils import cstr, flt, fmt_money, formatdate, getdate, nowdate, cint, get_link_to_form
from frappe import msgprint, _, scrub
from erpnext.controllers.accounts_controller import AccountsController
from dateutil.relativedelta import relativedelta
from erpnext.accounts.utils import get_balance_on, get_stock_accounts, get_stock_and_account_balance, \
	get_account_currency
from erpnext.accounts.party import get_party_account
from erpnext.hr.doctype.expense_claim.expense_claim import update_reimbursed_amount
from erpnext.accounts.doctype.invoice_discounting.invoice_discounting \
	import get_party_account_based_on_invoice_discounting
from erpnext.accounts.deferred_revenue import get_deferred_booking_accounts
from frappe.model.document import Document
from six import string_types, iteritems



class CommissionPayment(Document):
	pass

	def validate(self):
		if self.total_payable ==0:
			self.get_details()

	def on_submit(self):
		if self.pay_to == "Sales Partner":
			self.update_invoice_partner1()
			self.make_jv_partner()
		elif self.pay_to == "Sales Manager":
			self.update_invoice_manager1()
			self.make_jv_manager()
		elif self.pay_to == "Sales Supervisor":
			self.update_invoice_super1()
			self.make_jv_super()
	def on_cancel(self):
		if self.pay_to == "Sales Partner":
			self.update_invoice_partner0()
		elif self.pay_to == "Sales Manager":
			self.update_invoice_manager0()
		elif self.pay_to == "Sales Supervisor":
			self.update_invoice_super0()

	@frappe.whitelist()
	def get_details(self):
		if self.pay_to =="Sales Partner":
			invoices =frappe.db.sql(""" select name as name ,
										customer as customer,
										posting_date as posting_date,
										net_total as net_total,
										outstanding_amount as outstanding,
										sales_partner_commission as commissions
										from `tabSales Invoice` 
										where 
										docstatus = 1 
										and paid = 0 
										and sales_partner = %s 
										and outstanding_amount = 0
										and posting_date > '2019-12-31'
										and sales_partner_commission != 0""", self.sales_partner, as_dict=True)
			for comm in invoices:
				row = self.append('commission_details', {})
				row.sales_invoice = comm.name
				row.customer = comm.customer
				row.posting_date = comm.posting_date
				row.net_total = comm.net_total
				row.outstanding = comm.outstanding
				row.commissions = comm.commissions

		elif self.pay_to =="Sales Manager":

			invoices = frappe.db.sql(""" select name	 as name ,
										customer as customer,
										posting_date as posting_date,
										net_total as net_total,
										outstanding_amount as outstanding,
										sales_manager_commission as commissions
										from `tabSales Invoice` 
										where 
										docstatus=1 
										and paid2 =0 
										and sales_manager = %s 
										and outstanding_amount = 0
										and posting_date > '2020-12-31'
										 and sales_manager_commission != 0""", self.sales_manager, as_dict=True)
			for comm in invoices:
				row = self.append('commission_details', {})
				row.sales_invoice = comm.name
				row.customer = comm.customer
				row.posting_date = comm.posting_date
				row.net_total = comm.net_total
				row.outstanding = comm.outstanding
				row.commissions = comm.commissions


		elif self.pay_to =="Sales Supervisor":

			invoices = frappe.db.sql(""" select name	 as name ,
										customer as customer,
										posting_date as posting_date,
										net_total as net_total,
										outstanding_amount as outstanding,
										supervisor_commission as commissions
										from `tabSales Invoice` 
										where 
										docstatus=1 
										and paid2 =0 
										and sales_manager = %s 
										and outstanding_amount = 0
										and posting_date > '2020-12-31'
										 and sales_manager_commission != 0""", self.sales_manager, as_dict=True)
			for comm in invoices:
				row = self.append('commission_details', {})
				row.sales_invoice = comm.name
				row.customer = comm.customer
				row.posting_date = comm.posting_date
				row.net_total = comm.net_total
				row.outstanding = comm.outstanding
				row.commissions = comm.commissions

				
	def update_invoice_partner1(self):
		for inv in self.commission_details:
			frappe.db.sql("""  update `tabSales Invoice` set paid = 1 where name = %s """,inv.sales_invoice)

	def update_invoice_super1(self):
		for inv in self.commission_details:
			frappe.db.sql("""  update `tabSales Invoice` set paid_3 = 1 where name = %s """,inv.sales_invoice)

	def update_invoice_partner0(self):
		for inv in self.commission_details:
			frappe.db.sql("""  update `tabSales Invoice` set paid_3 = 0 where name = %s """,inv.sales_invoice)

	def update_invoice_super0(self):
		for inv in self.commission_details:
			frappe.db.sql("""  update `tabSales Invoice` set paid = 0 where name = %s """,inv.sales_invoice)

	def update_invoice_manager1(self):
		for inv in self.commission_details:
			frappe.db.sql("""  update `tabSales Invoice` set paid2 = 1 where name = %s """,inv.sales_invoice)

	def update_invoice_manager0(self):
		for inv in self.commission_details:
			frappe.db.sql("""  update `tabSales Invoice` set paid2 = 0 where name = %s """,inv.sales_invoice)

	@frappe.whitelist()

	def make_jv_manager(self):
		company = frappe.db.get_value("Company", frappe.db.get_value("Global Defaults", None, "default_company"),"company_name")
		accounts = [
			{
				"account": self.sales_manager_account,
				"debit_in_account_currency": self.total_payable,
				"exchange_rate": "1"
			},
			{
				"account": self.payment_account,
				"credit_in_account_currency": self.total_payable,
				"exchange_rate": "1"
			}
		]
		doc = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"commission_payment": self.name,
			"company": company,
			"posting_date": self.posting_date,
			"accounts": accounts,
			"cheque_no": self.name,
			"cheque_date": self.posting_date,
			"user_remark": _('Accrual Journal Entry for Sales Commission for {0}').format(self.sales_partner),
			"total_debit": self.total_payable,
			"total_credit": self.total_payable,
			"remark":  _('Accrual Journal Entry for Sales Commission for {0}').format(self.sales_partner)

		})
		doc.insert()
		doc.submit()

	def make_jv_partner(self):
		company = frappe.db.get_value("Company", frappe.db.get_value("Global Defaults", None, "default_company"),"company_name")
		accounts = [
			{
				"account": self.sales_partner_account,
				"debit_in_account_currency": self.total_payable,
				"exchange_rate": "1"
			},
			{
				"account": self.payment_account,
				"credit_in_account_currency": self.total_payable,
				"exchange_rate": "1"
			}
		]
		doc = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"commission_payment": self.name,
			"company": company,
			"posting_date": self.posting_date,
			"accounts": accounts,
			"cheque_no": self.name,
			"cheque_date": self.posting_date,
			"user_remark": _('Accrual Journal Entry for Sales Commission for {0}').format(self.sales_partner),
			"total_debit": self.total_payable,
			"total_credit": self.total_payable,
			"remark":  _('Accrual Journal Entry for Sales Commission for {0}').format(self.sales_partner)

		})
		doc.insert()
		doc.submit()

	def make_jv_super(self):
			company = frappe.db.get_value("Company", frappe.db.get_value("Global Defaults", None, "default_company"),"company_name")
			accounts = [
				{
					"account": self.sales_partner_account,
					"debit_in_account_currency": self.total_payable,
					"exchange_rate": "1"
				},
				{
					"account": self.payment_account,
					"credit_in_account_currency": self.total_payable,
					"exchange_rate": "1"
				}
			]
			doc = frappe.get_doc({
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"commission_payment": self.name,
				"company": company,
				"posting_date": self.posting_date,
				"accounts": accounts,
				"cheque_no": self.name,
				"cheque_date": self.posting_date,
				"user_remark": _('Accrual Journal Entry for Sales Commission for {0}').format(self.sales_partner),
				"total_debit": self.total_payable,
				"total_credit": self.total_payable,
				"remark":  _('Accrual Journal Entry for Sales Commission for {0}').format(self.sales_partner)

			})
			doc.insert()
			doc.submit()
