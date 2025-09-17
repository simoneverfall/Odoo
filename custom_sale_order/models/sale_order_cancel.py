from odoo import models,fields,api,_

class SaleOrderCancel(models.TransientModel):
    _inherit = 'sale.order.cancel'

    def action_send_mail_and_cancel(self):
        self.ensure_one()
        self.order_id.message_post(
            author_id=self.author_id.id,
            body=self.body,
            message_type='comment',
            email_layout_xmlid='mail.mail_notification_light',
            partner_ids=self.recipient_ids.ids,
            subject=self.subject,
        )

        self.order_id.partner_id.message_post(
            author_id=self.author_id.id,
            body=self.body,
            message_type='comment',
            email_layout_xmlid='mail.mail_notification_light',
            partner_ids=self.recipient_ids.ids,
            subject=self.subject,
        )
        return self.action_cancel()