from odoo import _, api, models, modules, tools

class AccountMoveSend(models.AbstractModel):
    _inherit="account.move.send"

    @api.model
    def _send_mail(self, move, mail_template, **kwargs):
        """ Send the journal entry passed as parameter by mail. """
        partner_ids = kwargs.get('partner_ids', [])
        author_id = kwargs.pop('author_id')

        new_message = move\
            .with_context(
                no_new_invoice=True,
                mail_notify_author=author_id in partner_ids,
                email_notification_allow_footer=True,
            ).message_post(
                message_type='comment',
                **kwargs,
                **{  # noqa: PIE804
                    'email_layout_xmlid': self._get_mail_layout(),
                    'email_add_signature': not mail_template,
                    'mail_auto_delete': mail_template.auto_delete,
                    'mail_server_id': mail_template.mail_server_id.id,
                    'reply_to_force_new': False,
                }
            )

        move.partner_id.message_post(
            body=new_message.body,
            subject=new_message.subject,
            message_type='comment',
            subtype_xmlid='mail.mt_comment'
        )

        # new_message_for_partner = move.partner_id\
        #     .with_context(
        #         no_new_invoice=True,
        #         mail_notify_author=author_id in partner_ids,
        #         email_notification_allow_footer=True,
        #     ).message_post(
        #         message_type='comment',
        #         **kwargs,
        #         **{  # noqa: PIE804
        #             'email_layout_xmlid': self._get_mail_layout(),
        #             'email_add_signature': not mail_template,
        #             'mail_auto_delete': mail_template.auto_delete,
        #             'mail_server_id': mail_template.mail_server_id.id,
        #             'reply_to_force_new': False,
        #         }
        #     )