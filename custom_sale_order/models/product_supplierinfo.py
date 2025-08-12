# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models,fields


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