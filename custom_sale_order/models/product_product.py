from odoo import models, fields, api,_
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    margin_percent = fields.Float(
        string='Margin %',
        help='Enter the desired profit margin percentage. Sale price will update automatically.',
        default=30
    )

    @api.onchange('standard_price', 'margin_percent')
    def _compute_sale_price(self):
        if self.margin_percent > 100:
            raise ValidationError(_('Margin cannot be equal to or greater than 100%. Please input a lower value.'))

        for product in self:
            if product.standard_price and product.margin_percent is not None:
                denominator = 1 - (product.margin_percent / 100)
                if denominator != 0:  # avoid division by zero
                    product.list_price = product.standard_price / denominator
                else:
                    product.list_price = 0  # or set to cost, or raise ValidationError
            else:
                product.list_price = product.standard_price

