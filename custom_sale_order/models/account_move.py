# -*- coding: utf-8 -*-

from odoo import _,api, fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    client_photo_ids = fields.Many2many(
        'ir.attachment',
        'account_move_attachment_rel',
        'move_id',
        'attachment_id',
        string='Client Photos',
        domain=[('type', '=', 'binary')],
    )
    details = fields.Char(string="Details", related="partner_shipping_id.street")
    client_name = fields.Char(string="Client Name", related="partner_shipping_id.name")
    provider_name = fields.Char(string="Provider Name", related="partner_id.name")
    suburb = fields.Char(
        string="Suburb",
        related="partner_shipping_id.city",
        store=True,  # Optional: store in DB if you need it in filters or views
        readonly=True
    )