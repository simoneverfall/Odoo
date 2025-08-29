from odoo import api, models,fields


class ProjectTask(models.Model):
    _inherit = "project.task"

    sale_order_ref = fields.Many2one('sale.order', string='Sale Order', ondelete='set null')