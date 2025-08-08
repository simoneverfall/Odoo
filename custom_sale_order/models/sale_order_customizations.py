# -*- coding: utf-8 -*-

from odoo import _,api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state_custom = fields.Selection([
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
        ('hold', 'Hold'),
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
    suburb = fields.Char(
        string="Suburb",
        related="partner_shipping_id.state_id.name",
        store=True,  # Optional: store in DB if you need it in filters or views
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            project = order._create_project_task_for_order()
            order.project_id = project.id
        return orders

    def _create_project_task_for_order(self):
        partner = self.partner_shipping_id
        if partner:
            client_parts = [partner.name, partner.street, partner.city, partner.phone]
            client_details = ", ".join([part for part in client_parts if part])
        project = self.env['project.project'].create({
            'name': f"Project {self.name} ",
        })
        self.env['project.task'].create({
            'name': client_details ,
            'project_id': project.id,
        })
        return project

    # Remove the note (terms and conditions) so it does not carry over to the invoice
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.pop('narration', None)
        return invoice_vals

class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        # Try to get product template ID from context
        product_tmpl_id = self.env.context.get('default_product_tmpl_id')

        if product_tmpl_id:
            product_tmpl = self.env['product.template'].browse(product_tmpl_id)
            if 'price' in fields_list and product_tmpl.standard_price:
                defaults['price'] = product_tmpl.standard_price

        return defaults