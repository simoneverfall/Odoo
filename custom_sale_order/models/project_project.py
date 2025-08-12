# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models,fields


class ProjectProject(models.Model):
    _inherit = "project.project"


    sale_order_ref = fields.Many2one('sale.order', string='Sale Order', ondelete='set null')
