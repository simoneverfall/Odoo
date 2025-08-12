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
