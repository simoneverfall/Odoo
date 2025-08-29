# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _,api, fields, models
from odoo.exceptions import UserError


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
        domain=[('type', '=', 'binary')],
    )
    details = fields.Char(string="Details",related="partner_shipping_id.street")
    client_name = fields.Char(string="Suburb",related="partner_shipping_id.name")
    provider_name = fields.Char(string="Case Manager",related="partner_id.name")
    suburb = fields.Char(
        string="Suburb",
        related="partner_shipping_id.city",
        store=True,  # Optional: store in DB if you need it in filters or views
        readonly=True
    )

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
        default_confirmation_template_id = self.env['ir.config_parameter'].sudo().get_param(
            'sale.default_confirmation_template'
        )
        default_confirmation_template = default_confirmation_template_id \
            and self.env['mail.template'].browse(int(default_confirmation_template_id)).exists()
        if default_confirmation_template:
            return default_confirmation_template
        else:
            return self.env.ref('custom_sale_order.mail_template_sale_confirmation', raise_if_not_found=False)

