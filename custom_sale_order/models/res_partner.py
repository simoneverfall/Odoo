import re
from odoo import _,api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    sent_mails_count = fields.Integer(compute="_compute_sent_mails_count")

    received_mails_count = fields.Integer(compute="_compute_received_mails_count")

    def _compute_display_name(self):
        if self.env.context.get("only_name"):

            for partner in self:
                name = partner.name or ''
                if partner._context.get('show_address'):
                    name = name + "\n" + partner._display_address(without_company=True)
                name = re.sub(r'\s+\n', '\n', name)
                if partner._context.get('partner_show_db_id'):
                    name = f"{name} ({partner.id})"
                if partner._context.get('address_inline'):
                    splitted_names = name.split("\n")
                    name = ", ".join([n for n in splitted_names if n.strip()])
                if partner._context.get('show_email') and partner.email:
                    name = f"{name} <{partner.email}>"
                if partner._context.get('show_vat') and partner.vat:
                    name = f"{name} ‒ {partner.vat}"

                partner.display_name = name.strip()
        elif self.env.context.get("only_company"):
            for partner in self:
                name = partner.parent_id.name or partner.name or ''
                partner.display_name = name.strip()
        else:
            super()._compute_display_name()

    
    def _compute_sent_mails_count(self):
        self.ensure_one()
        self.sent_mails_count = self.env['mail.message'].sudo().search_count([('partner_ids', 'in', self.ids)])

    def _compute_received_mails_count(self):
        self.ensure_one()
        self.received_mails_count = self.env['mail.message'].sudo().search_count([('author_id', 'in', self.ids)])
        

    # For Smart Button Logic

    def action_partner_received_mail(self):
        self.ensure_one()
        action = self.env.ref('mail.action_view_mail_message').read()[0]
        action['domain'] = [('author_id', 'in', self.ids)]
        return action
    
    def action_partner_send_mail(self):
        self.ensure_one()
        action = self.env.ref('mail.action_view_mail_message').read()[0]
        action['domain'] = [('partner_ids', 'in', self.ids)]
        return action
