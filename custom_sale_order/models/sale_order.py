# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _,api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_state_custom = fields.Selection([
        ('complete', 'Complete'),
        ('approved', 'Approved'),
        ('awaiting_approval','Awaiting Approval'),
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
        ('hold', 'Hold'),
        ('to_quote', 'To Quote'),
        ('no_quote_required', 'No Quote Required'),
        ('follow_up', 'Follow up'),
        ('material_ord', 'Materials  Ordered'),
    ], string="Order Status")
    project_id = fields.Many2one('project.project',string="Project")
    task_id = fields.Many2one('project.task',string="Task")
    client_photo_ids = fields.Many2many(
        'ir.attachment',
        'sale_order_attachment_rel',
        'sale_order_id',
        'attachment_id',
        string='Client Photos',
        domain=[('mimetype', 'ilike', 'image/')],
    )

    # Partner Shipping (Is actually the client)
    # Client needs to be partner_id
    # Case manager is being shifted to Delivery Address Field.


    # details = fields.Char(string="Details",related="partner_shipping_id.street")
    details = fields.Char(string="Details",related="partner_id.street")

    # client_name = fields.Char(string="Suburb",related="partner_shipping_id.name")
    client_name = fields.Char(string="Suburb",related="partner_id.name")

    # provider_name = fields.Char(string="Case Manager",related="partner_id.name")

    # suburb = fields.Char(
    #     string="Suburb",
    #     related="partner_shipping_id.city",
    #     store=True,  # Optional: store in DB if you need it in filters or views
    #     readonly=True
    # )
    suburb = fields.Char(
        string="Suburb",
        related="partner_id.city",
        store=True,  # Optional: store in DB if you need it in filters or views
        readonly=True
    )

    provider_id = fields.Many2one('res.partner')

    case_manager_id = fields.Many2one('res.partner')


    @api.constrains('client_photo_ids')
    def _check_client_photo_ids(self):
        for order in self:
            for attachment in order.client_photo_ids:
                if not (attachment.mimetype or "").startswith("image/"):
                    raise ValidationError(_("Only image files are allowed in Client Photos."))

    @api.model
    def create(self, vals):
        order = super().create(vals)
        if vals.get("x_state_custom") == "booked":
            order._send_booked_email()
        if vals.get("x_state_custom") == "complete":
            order._send_completion_email()
        return order

    def write(self, vals):
        res = super().write(vals)
        if vals.get("x_state_custom") == "booked":
            for order in self:
                order._send_booked_email()
        if vals.get("x_state_custom") == "complete":
            for order in self:
                order._send_completion_email()
        return res

    def _send_completion_email(self):
        template = self.env.ref('custom_sale_order.email_template_sale_order_complete')
        print('------?',template)
        for order in self:
            if order.partner_id.email:
                template.send_mail(order.id, force_send=True)
    def _send_booked_email(self):
        template = self.env.ref('custom_sale_order.email_template_sale_order_booked')
        for order in self:
            if order.partner_id.email:
                template.send_mail(order.id, force_send=True)

    def _create_project_task_for_order(self, note_text=None):
        partner = self.partner_shipping_id
        if partner:
            client_parts = [partner.name, partner.street, partner.city, partner.phone]
            client_details = ", ".join([part for part in client_parts if part])
        else:
            client_details = ''

        # Create Project with note as description if provided
        project = self.env['project.project'].create({
            'name': f"Project {self.name}",
            'sale_order_ref': self.id
        })
        self.project_id = project
        task = self.env['project.task'].create({
            'name': client_details,
            'sale_order_ref': self.id,
            'project_id': project.id,
            'description': note_text or '',
            'planned_date_begin': fields.Datetime.now(),  # Start = now
            'date_deadline': fields.Datetime.now() + timedelta(hours=8),  # Deadline = +8 hours
        })
        self.task_id = task



    # Remove the note (terms and conditions) so it does not carry over to the invoice
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.pop('narration', None)
        # Add client photos from sale order to invoice
        if self.client_photo_ids:
            invoice_vals['client_photo_ids'] = [(6, 0, self.client_photo_ids.ids)]
        return invoice_vals

    def action_confirm(self):
        for order in self:
            if not order.order_line:
                raise UserError("You must add at least one line before confirming the sale order.")

            first_line = order.order_line[0]
            if first_line.display_type != 'line_note':
                raise UserError("The first line of the sale order must be a Note.")

            note_text = first_line.name

            res = super(SaleOrder, order).action_confirm()

            # Create project with the note
            if not order.project_id:
                order._create_project_task_for_order(note_text=note_text)

        return res

    def action_open_task_calendar(self):
        """Open calendar view for the related task activities"""
        return {
            "type": "ir.actions.act_window",
            "name": f"Calendar for {self.task_id.display_name}",
            "res_model": "project.task",
            "view_mode": "calendar,list,form",
            "context": {
                "search_default_project_id": self.project_id.id,  # filter by project
                "initial_date": self.task_id.planned_date_begin,
            },
        }

    def _find_mail_template(self):
        """ Get the appropriate mail template for the current sales order based on its state.

        If the SO is confirmed, we return the mail template for the sale confirmation.
        Otherwise, we return the quotation email template.

        :return: The correct mail template based on the current status
        :rtype: record of `mail.template` or `None` if not found
        """
        self.ensure_one()
        if self.env.context.get('proforma') or self.state != 'sale':
            return self.env.ref('custom_sale_order.email_template_edi_salex', raise_if_not_found=False)
        else:
            return self._get_confirmation_template()

    def _get_confirmation_template(self):
        """ Get the mail template sent on SO confirmation (or for confirmed SO's).

        :return: `mail.template` record or None if default template wasn't found
        """
        self.ensure_one()
        return self.env.ref('custom_sale_order.mail_template_sale_confirmation', raise_if_not_found=False)
    

    def swap_partner_id_and_partner_shipping_id(self):
        for record in self:
            _logger.info('Swaping For %s has started', record.name)
            partner_obj = record.partner_id
            partner_shipping_obj = record.partner_shipping_id
            partner_invoice_obj = record.partner_invoice_id
            _logger.info('Before Swapped Partner_Id --> %s  Shipping Id --> %s', record.partner_id.display_name,record.partner_shipping_id.display_name)
            record.sudo().write(
                {
                    'partner_id': partner_shipping_obj.id,
                    'partner_shipping_id': partner_obj.id,
                    'provider_id': partner_invoice_obj.id,
                    'case_manager_id': partner_obj.id
                }
            )
            _logger.info('Swapped Partner_Id --> %s  Shipping Id --> %s', record.partner_id.display_name,record.partner_shipping_id.display_name)
    
        # INVOICING #
        # To Create invoice for the Provider Field
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()

        txs_to_be_linked = self.transaction_ids.sudo().filtered(
            lambda tx: (
                tx.state in ('pending', 'authorized')
                or tx.state == 'done' and not (tx.payment_id and tx.payment_id.is_reconciled)
            )
        )

        values = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.provider_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(self.provider_id)).id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_user_id': self.user_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [Command.set(txs_to_be_linked.ids)],
            'company_id': self.company_id.id,
            'invoice_line_ids': [],
            'user_id': self.user_id.id,
        }
        if self.journal_id:
            values['journal_id'] = self.journal_id.id
        return values


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        template = self.env.ref('custom_sale_order.email_template_invoice_confirmation')
        _logger.info(f"name of the template {template}")
        sale_orders = self.sale_order_ids
        for order in sale_orders:
            _logger.info(f"sale order name  {order.name}")
            if order.partner_id.email:
                _logger.info(f"sale order name  {order.partner_id.email}")
                template.send_mail(order.id, force_send=True)
                _logger.info(f"email sent ")
        return super(SaleAdvancePaymentInv, self).create_invoices()