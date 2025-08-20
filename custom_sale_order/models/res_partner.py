import re
from odoo import _,api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

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
