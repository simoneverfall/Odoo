# -*- coding: utf-8 -*-

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
        ('to_quote_required', 'To Quote Required'),
    ], string="Order Status")
    project_id = fields.Many2one('project.project',string="Project")
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
    provider_name = fields.Char(string="Provider",related="partner_id.name")
    suburb = fields.Char(
        string="Suburb",
        related="partner_shipping_id.city",
        store=True,  # Optional: store in DB if you need it in filters or views
        readonly=True
    )

    # @api.model_create_multi
    # def create(self, vals_list):
    #     orders = super().create(vals_list)
    #     for order in orders:
    #         project = order._create_project_task_for_order()
    #         order.project_id = project.id
    #     return orders
    #
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
        # Create related task
        self.env['project.task'].create({
            'name': client_details,
            'project_id': project.id,
            'description': note_text or '',
        })


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

