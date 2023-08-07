from __future__ import unicode_literals
import frappe
from frappe import _


@frappe.whitelist()
def before_insert(doc, method=None):
    pass
@frappe.whitelist()
def after_insert(doc, method=None):
    pass
@frappe.whitelist()
def onload(doc, method=None):
    pass
@frappe.whitelist()
def before_validate(doc, method=None):
    pass
@frappe.whitelist()
def validate(doc, method=None):
    pass
@frappe.whitelist()
def on_submit(doc, method=None):
    pass
@frappe.whitelist()
def on_cancel(doc, method=None):
    pass
@frappe.whitelist()
def on_update_after_submit(doc, method=None):
    pass
@frappe.whitelist()
def before_save(doc, method=None):
    pass
@frappe.whitelist()
def before_cancel(doc, method=None):
    pass
@frappe.whitelist()
def on_update(doc, method=None):
    pass


# method to make taxes JV
@frappe.whitelist()
def validate_taxe_type(self):
    if self.tax_type == "Included":
        for y in self.items:
            group = y.item_group
            item_taxes_template = frappe.db.sql(
                """ select item_tax_template from `tabItem Tax` where parent=%s """, group, as_dict=1)
            for z in item_taxes_template:
                y.item_tax_template = z.item_tax_template
        for x in self.taxes:
            x.included_in_print_rate = 1
    if self.tax_type == "Excluded":
        for y in self.items:
            group = y.item_group
            item_taxes_template = frappe.db.sql(
                """ select item_tax_template from `tabItem Tax` where parent=%s """, group, as_dict=1)
            for z in item_taxes_template:
                y.item_tax_template = z.item_tax_template
        for x in self.taxes:
            x.included_in_print_rate = 0
    if self.tax_type == "Commercial":
        for x in self.items:
            x.item_tax_template = ""
        self.set("taxes", [])

@frappe.whitelist()
def make_tax(name):
    self = frappe.get_doc("Sales Invoice", name)
    default_tax_acc = frappe.db.get_value("Company", self.company, "default_taxes")
    deferred_tax_acc = frappe.db.get_value("Company", self.company, "deferred_tax")
    default_income_account = frappe.db.get_value("Company", self.company, "default_income_account")
    default_receivable_account = frappe.db.get_value("Company", self.company, "default_receivable_account")
    # if self.deferred_tax_jv:
    #	frappe.throw(_("لايمكن انشاء القيود مرة اخرى !"))
    if self.tax_type in ("Included", "Excluded"):
        accounts = [
            {
                "doctype": "Journal Entry Account",
                "account": default_tax_acc,
                "debit": 0,
                "credit": self.total_taxes_and_charges,
                "credit_in_account_currency": self.total_taxes_and_charges,
                "user_remark": self.name
            },
            {
                "doctype": "Journal Entry Account",
                "account": deferred_tax_acc,
                "debit": self.total_taxes_and_charges,
                "credit": 0,
                "debit_in_account_currency": self.total_taxes_and_charges,
                "user_remark": self.name
            }
        ]
        doc = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Deferred Revenue",
            "sales_invoice": self.name,
            "company": self.company,
            "posting_date": self.posting_date,
            "accounts": accounts,
            "user_remark": _('ترحيل مخصص الضرائب  {0}').format(self.name),
            "total_debit": self.total_taxes_and_charges,
            "total_credit": self.total_taxes_and_charges,
            "remark": _('ترحيل مخصص الضرائب  {0}').format(self.name)

        })
        doc.insert()
        doc.submit()
        djv = doc.name
        docs = frappe.get_doc('Sales Invoice', self.name)
        docs.deferred_tax_jv = djv
        docs.save()
        if not self.serial:
            serial = frappe.get_doc({
                "doctype": "Invoice Serial",
                "link": self.name,
                "status": "Active"
            })
            serial.insert()
            docs.serial = serial.name
        else:
            serial = frappe.get_doc('Invoice Serial', self.serial)
            serial.status = "Active"
            serial.save()
            docs.serial = serial.name
        docs.save()

    elif self.tax_type == "Commercial":
        # taxes_amount = float(self.grand_total) - (float(self.grand_total) / 1.14)
        grand_tax_amount = 0
        for y in self.items:
            group = y.item_group
            item_taxes_template = frappe.db.get_value('Item Tax', {'parent': group}, ['item_tax_template'])
            item_taxes_rate = frappe.db.get_value('Item Tax Template Detail', {'parent': item_taxes_template},
                                                    ['tax_rate'])
            tax_rate = item_taxes_rate / 100
            grand_tax_amount += tax_rate * y.amount

        accounts = [
            {
                "doctype": "Journal Entry Account",
                "account": default_tax_acc,
                "debit": 0,
                "credit": grand_tax_amount,
                "credit_in_account_currency": grand_tax_amount,
                "user_remark": self.name
            },
            {
                "doctype": "Journal Entry Account",
                "account": default_receivable_account,
                "debit": grand_tax_amount,
                "party_type": "Customer",
                "party": self.customer,
                "credit": 0,
                "debit_in_account_currency": grand_tax_amount,
                "user_remark": self.name
            }
        ]
        doc = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Deferred Revenue",
            "sales_invoice": self.name,
            "company": self.company,
            "posting_date": self.posting_date,
            "accounts": accounts,
            "user_remark": _('ترحيل مخصص الضرائب  {0}').format(self.name),
            "total_debit": grand_tax_amount,
            "total_credit": grand_tax_amount,
            "remark": _('ترحيل مخصص الضرائب  {0}').format(self.name)

        })
        doc.insert()
        doc.submit()
        djv = doc.name
        docs = frappe.get_doc('Sales Invoice', self.name)
        docs.deferred_tax_jv = djv

        if not self.serial:
            serial = frappe.get_doc({
                "doctype": "Invoice Serial",
                "link": self.name,
                "status": "Active"
            })
            serial.insert()
            docs.serial = serial.name
        else:
            serial = frappe.get_doc('Invoice Serial', self.serial)
            serial.status = "Active"
            serial.save()
            docs.serial = serial.name
        docs.save()
    self.reload()

@frappe.whitelist()
def cancel_tax(self):
    if self.deferred_tax_jv or self.serial:
        inv = frappe.get_doc('Sales Invoice', self.name)
        inv.deferred_tax_jv = ""
        jv = frappe.get_doc('Journal Entry', self.deferred_tax_jv)
        jv.sales_invoice = ""
        serial = frappe.get_doc('Invoice Serial', self.serial)
        serial.status = "Cancelled"
        inv.save()
        jv.save()
        serial.save()
        jv.cancel()
        delete = frappe.delete_doc("Invoice Serial", self.serial)
        self.serial = ""
        frappe.db.set_value("Sales Invoice", self.name, "serial", "")
        frappe.db.commit()
        self.reload()
        return delete
