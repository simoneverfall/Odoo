import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
import requests
import json
import base64
import logging
from lxml import etree

from odoo.tools import frozendict

_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit="account.move"


    @api.model
    def prepare_invoice_export_dict(self):
        if self._context.get('cron'):
            company = self.company_id
        else:
            # company = self.env['res.users'].search([('id', '=', self._uid)], limit=1).company_id
            company = self.company_id
            if not company:
                company = self.env['res.users'].search([('id', '=', self._uid)], limit=1).company_id
        if self.move_type == 'in_invoice':
            vals = self.prepare_vendorbill_export_dict()
            return vals
        else:

            if self.env.user.company_id.export_bill_parent_contact and self.partner_id.parent_id:
                cust_id = self.env['res.partner'].get_xero_partner_ref(self.partner_id.parent_id)
            else:
                cust_id = self.env['res.partner'].get_xero_partner_ref(self.partner_id)

            vals = {}
            lst_line = []
            origin_reference = ''
            if self.move_type == 'in_invoice':
                type = 'ACCPAY'
            elif self.move_type == 'out_invoice':
                type = 'ACCREC'
            elif self.move_type == 'in_refund':
                type = 'ACCPAYCREDIT'
            elif self.move_type == 'out_refund':
                type = 'ACCRECCREDIT'

            # if company.map_invoice_reference == 'customer_ref':
            #     if self.ref:
            #         origin_reference = self.ref
            # elif company.map_invoice_reference == 'payment_ref':
            #     if self.payment_reference:
            #         origin_reference = self.payment_reference

            if self.partner_shipping_id and self.partner_shipping_id.contact_address_complete:
                origin_reference = f"{self.partner_shipping_id.name} - {self.partner_shipping_id.contact_address_complete}"

            if self.partner_shipping_id and not self.partner_shipping_id.contact_address_complete:
                origin_reference = self.partner_shipping_id.name

            if self.tax_state:
                if self.tax_state == 'inclusive':
                    tax_state = 'Inclusive'
                elif self.tax_state == 'exclusive':
                    tax_state = 'Exclusive'
                elif self.tax_state == 'no_tax':
                    tax_state = 'NoTax'

            if self.state:
                if self.state == 'posted':
                    status = 'AUTHORISED'

                if company.invoice_status:
                    if company.invoice_status == 'draft':
                        status = 'DRAFT'
                    if company.invoice_status == 'authorised':
                        status = 'AUTHORISED'

            if len(self.invoice_line_ids) == 1:
                single_line = self.invoice_line_ids
                Tracking_list = []
                if single_line.analytic_distribution:
                    for analytic_dist_id, amount in single_line.analytic_distribution.items():
                        # Check if the key is a combined key (e.g., '1,2')
                        if ',' in analytic_dist_id:
                            # Split the combined key into individual IDs
                            analytic_dist_ids = analytic_dist_id.split(',')
                        else:
                            # If it's a single ID, make it a list for consistency
                            analytic_dist_ids = [analytic_dist_id]

                        # Ensure the IDs are valid by converting them to integers if necessary
                        analytic_dist_ids = [int(id) for id in analytic_dist_ids]

                        # Use the 'in' operator to search for multiple IDs
                        analytic_account_id = self.env['account.analytic.account'].search(
                            [('id', 'in', analytic_dist_ids)]
                        )

                        for rec in analytic_account_id:
                            rec.create_analytic_account_in_xero(account_id=rec.id)
                            Tracking_list.append({'Name': rec.plan_id.name, 'Option': rec.name})
                    # for analytic_dist_id in single_line.analytic_distribution:
                    #     analytic_account_id = self.env['account.analytic.account'].search(
                    #         [('id', '=', analytic_dist_id)])
                    #     analytic_account_id.create_analytic_account_in_xero(
                    #         account_id=analytic_account_id.id)
                    #     Tracking_list.append({'Name': analytic_account_id.plan_id.name,
                    #                           'Option': analytic_account_id.name})

                if single_line.quantity < 0:
                    qty = -single_line.quantity
                    price = -single_line.price_unit
                else:
                    qty = single_line.quantity
                    price = single_line.price_unit

                if single_line.discount:
                    discount = single_line.discount
                else:
                    discount = 0.0

                if single_line.account_id:
                    if single_line.account_id.xero_account_id:
                        account_code = single_line.account_id.code
                    else:
                        self.env['account.account'].create_account_ref_in_xero(single_line.account_id)
                        if single_line.account_id.xero_account_id:
                            account_code = single_line.account_id.code

                if single_line.product_id and not company.export_invoice_without_product:
                    if single_line.product_id.xero_product_id:
                        _logger.info(_("PRODUCT DEFAULT CODE AVAILABLE"))
                    elif not single_line.product_id.xero_product_id:
                        self.env['product.product'].get_xero_product_ref(single_line.product_id)

                    if single_line.tax_ids:
                        line_tax = self.env['account.tax'].search(
                            [('id', '=', single_line.tax_ids.id), ('company_id', '=', company.id)])
                        if line_tax:
                            tax = line_tax.xero_tax_type_id
                            if not tax:
                                self.env['account.tax'].get_xero_tax_ref(line_tax)
                                line_tax = self.env['account.tax'].search(
                                    [('id', '=', single_line.tax_ids.id), ('company_id', '=', company.id)])
                                tax = line_tax.xero_tax_type_id

                            vals.update({
                                "Contact": {
                                    "ContactID": cust_id
                                },
                                "Type": type,
                                "LineAmountTypes": tax_state,
                                "DueDate": str(self.invoice_date_due),
                                # "Date": str(self.invoice_date),
                                "Date": str(self.date if company.invoice_bill_accounting_date else self.invoice_date),
                                "Reference": origin_reference,
                                "InvoiceNumber": self.xero_invoice_number if (
                                        self.xero_invoice_number and self.xero_invoice_id) else self.name,
                                "LineItems": [
                                    {
                                        "Description": single_line.name,
                                        "Quantity": qty,
                                        "UnitAmount": price,
                                        "ItemCode": single_line.product_id.default_code,
                                        "AccountCode": account_code,
                                        "DiscountRate": discount,
                                        "Tracking": Tracking_list,
                                        "TaxType": tax
                                    }
                                ],
                                "Status": status
                            })


                    else:
                        vals.update({
                            # "Type": "ACCREC",
                            "Contact": {
                                "ContactID": cust_id
                            },
                            "Type": type,
                            "LineAmountTypes": tax_state,
                            "DueDate": str(self.invoice_date_due),
                            # "Date": str(self.invoice_date),
                            "Date": str(self.date if company.invoice_bill_accounting_date else self.invoice_date),
                            "Reference": origin_reference,
                            "InvoiceNumber": self.xero_invoice_number if (
                                    self.xero_invoice_number and self.xero_invoice_id) else self.name,
                            "LineItems": [
                                {
                                    "Description": single_line.name,
                                    "Quantity": qty,
                                    "UnitAmount": price,
                                    'ItemCode': single_line.product_id.default_code,
                                    "DiscountRate": discount,
                                    "Tracking": Tracking_list,
                                    "AccountCode": account_code
                                }
                            ],
                            "Status": status
                        })
                else:
                    if single_line.tax_ids:
                        line_tax = self.env['account.tax'].search(
                            [('id', '=', single_line.tax_ids.id), ('company_id', '=', company.id)])
                        if line_tax:
                            tax = line_tax.xero_tax_type_id
                            if not tax:
                                self.env['account.tax'].get_xero_tax_ref(line_tax)
                                line_tax = self.env['account.tax'].search(
                                    [('id', '=', single_line.tax_ids.id), ('company_id', '=', company.id)])
                                tax = line_tax.xero_tax_type_id

                            vals.update({
                                "Contact": {
                                    "ContactID": cust_id
                                },
                                "Type": type,
                                "LineAmountTypes": tax_state,
                                "DueDate": str(self.invoice_date_due),
                                # "Date": str(self.invoice_date),
                                "Date": str(self.date if company.invoice_bill_accounting_date else self.invoice_date),
                                "Reference": origin_reference,
                                "InvoiceNumber": self.xero_invoice_number if (
                                        self.xero_invoice_number and self.xero_invoice_id) else self.name,
                                "LineItems": [
                                    {
                                        "Description": single_line.name,
                                        "Quantity": qty,
                                        "UnitAmount": price,
                                        "AccountCode": account_code,
                                        "DiscountRate": discount,
                                        "Tracking": Tracking_list,
                                        "TaxType": tax
                                    }
                                ],
                                "Status": status
                            })
                    else:
                        vals.update({
                            "Contact": {
                                "ContactID": cust_id
                            },
                            "Type": type,
                            "DueDate": str(self.invoice_date_due),
                            # "Date": str(self.invoice_date),
                            "Date": str(self.date if company.invoice_bill_accounting_date else self.invoice_date),
                            "Reference": origin_reference,
                            "InvoiceNumber": self.xero_invoice_number if (
                                    self.xero_invoice_number and self.xero_invoice_id) else self.name,
                            "LineItems": [
                                {
                                    "Description": single_line.name,
                                    "DiscountRate": discount,
                                    "Quantity": qty,
                                    "UnitAmount": price,
                                    "Tracking": Tracking_list,
                                    "AccountCode": account_code
                                }
                            ],
                            "Status": status
                        })
            else:

                for line in self.invoice_line_ids:

                    if line.product_id and not company.export_invoice_without_product:
                        if line.product_id.xero_product_id:
                            _logger.info(_("PRODUCT DEFAULT CODE AVAILABLE"))
                        elif not line.product_id.xero_product_id:
                            self.env['product.product'].get_xero_product_ref(line.product_id)

                    line_vals = self.prepare_invoice_export_line_dict(line)
                    lst_line.append(line_vals)
                vals.update({
                    "Type": type,
                    "LineAmountTypes": tax_state,
                    "Contact": {"ContactID": cust_id},
                    "DueDate": str(self.invoice_date_due),
                    # "Date": str(self.invoice_date),
                    "Date": str(self.date if company.invoice_bill_accounting_date else self.invoice_date),
                    "Reference": origin_reference,
                    "InvoiceNumber": self.xero_invoice_number if (
                            self.xero_invoice_number and self.xero_invoice_id) else self.name,
                    "Status": status,
                    "LineItems": lst_line,
                })

            if self.currency_id:
                currency_code = self.currency_id.name
                vals.update({"CurrencyCode": currency_code})
            _logger.info('vals : {}'.format(vals))
            # Filter currency rates based on the given date
            # currency_rates = self.currency_id.rate_ids.filtered(lambda rate: self.invoice_date == rate.name)
            # # If currency rate is found, update the vals dictionary
            # if currency_rates:
            #     vals["CurrencyRate"] = currency_rates[0].company_rate
            if self.currency_id != company.currency_id:
                date = self.date if company.invoice_bill_accounting_date else self.invoice_date
                currency_rates = self.currency_id.rate_ids.filtered(lambda rate: date >= rate.name)
                if currency_rates:
                    currency_rates = max(currency_rates).company_rate
                else:
                    currency_rates = 1
                vals["CurrencyRate"] = currency_rates

            return vals
