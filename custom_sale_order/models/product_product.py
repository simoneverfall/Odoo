from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    margin_percent = fields.Float(
        string='Margin %',
        help='Enter the desired profit margin percentage. Sale price will update automatically.',
        default=30
    )

    def _calculate_list_price(self, cost, margin):
        """Helper to calculate sale price"""
        if margin >= 100:
            raise ValidationError(_('Margin cannot be equal to or greater than 100%.'))
        denominator = 1 - (margin / 100)
        return cost / denominator if denominator else 0

    @api.onchange('standard_price', 'margin_percent')
    def _onchange_margin_or_cost(self):
        """Update price in UI"""
        self.list_price = self._calculate_list_price(
            self.standard_price or 0,
            self.margin_percent or 0
        )

    def write(self, vals):
        """Save updated price"""
        if 'standard_price' in vals or 'margin_percent' in vals:
            cost = vals.get('standard_price', self.standard_price)
            margin = vals.get('margin_percent', self.margin_percent)
            vals['list_price'] = self._calculate_list_price(cost, margin)
        return super().write(vals)

    @api.model
    def create(self, vals):
        """Save price when creating"""
        cost = vals.get('standard_price', 0)
        margin = vals.get('margin_percent', 30)
        vals['list_price'] = self._calculate_list_price(cost, margin)
        return super().create(vals)
