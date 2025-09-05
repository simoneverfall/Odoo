from odoo import models, api, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    so_ref = fields.Char(string='So Reference')

    @api.model
    def create(self, vals):
        picking = super().create(vals)
        if picking.origin:
            sale_order = self.env['sale.order'].search([('name', '=', picking.origin)], limit=1)
            if sale_order:
                picking.so_ref = sale_order.name
        return picking

