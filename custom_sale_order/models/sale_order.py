# -*- coding: utf-8 -*-
from datetime import timedelta
from markupsafe import Markup       
from odoo import _,api, fields, models, Command
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_state_custom = fields.Selection([
        ('complete', 'Complete'),
        ('approved', 'Approved'),
        ('awaiting_approval','Awaiting Approval'),
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
        ('hold', 'Hold'),
        ('to_quote', 'To Quote'),
        ('no_quote_required', 'No Quote Required'),
        ('follow_up', 'Follow up'),
        ('material_ord', 'Materials  Ordered'),
    ], string="Order Status")
    project_id = fields.Many2one('project.project',string="Project")
    task_id = fields.Many2one('project.task',string="Task")
    client_photo_ids = fields.Many2many(
        'ir.attachment',
        'sale_order_attachment_rel',
        'sale_order_id',
        'attachment_id',
        string='Client Photos',
        domain=[('mimetype', 'ilike', 'image/')],
    )

    # Partner Shipping (Is actually the client)
    # Client needs to be partner_id
    # Case manager is being shifted to Delivery Address Field.


    # details = fields.Char(string="Details",related="partner_shipping_id.street")
    # details = fields.Char(string="Details",related="partner_id.street")
    details = fields.Char(string="Details",related="client_id.street")

    # client_name = fields.Char(string="Suburb",related="partner_shipping_id.name")
    client_name = fields.Char(string="Client Name",related="client_id.name")

    # provider_name = fields.Char(string="Case Manager",related="partner_id.name")

    # suburb = fields.Char(
    #     string="Suburb",
    #     related="partner_shipping_id.city",
    #     store=True,  # Optional: store in DB if you need it in filters or views
    #     readonly=True
    # )
    # suburb = fields.Char(
    #     string="Suburb",
    #     related="partner_id.city",
    #     store=True,  # Optional: store in DB if you need it in filters or views
    #     readonly=True
    # )
    suburb = fields.Char(
        string="Suburb",
        related="client_id.city",
        store=True,  # Optional: store in DB if you need it in filters or views
        readonly=True
    )

    provider_id = fields.Many2one('res.partner')

    case_manager_id = fields.Many2one('res.partner')

    # DUE TO ODOO EMAILS AND FLOW PARTNER ID IS GOING TO BE case manager id and client must be set as a seperate field.
    client_id = fields.Many2one('res.partner')

    custom_project_count = fields.Integer(compute="_compute_custom_project_count", store=True)

    custom_task_count = fields.Integer(compute="_compute_custom_task_count", store=True)


    @api.depends('project_id')
    def _compute_custom_project_count(self):
        for record in self:
            if record.project_id:
                record.custom_project_count = 1
            else:
                record.custom_project_count = 0
    
    @api.depends('task_id')
    def _compute_custom_task_count(self):
        for record in self:
            if record.task_id:
                record.custom_task_count = 1
            else:
                record.custom_task_count = 0


    @api.constrains('client_photo_ids')
    def _check_client_photo_ids(self):
        for order in self:
            for attachment in order.client_photo_ids:
                if not (attachment.mimetype or "").startswith("image/"):
                    raise ValidationError(_("Only image files are allowed in Client Photos."))

    @api.model
    def create(self, vals):
        order = super().create(vals)
        if vals.get("x_state_custom") == "booked":
            order._send_booked_email()
        if vals.get("x_state_custom") == "complete":
            order._send_completion_email()
        return order

    def write(self, vals):
        res = super().write(vals)
        if vals.get("x_state_custom") == "booked":
            for order in self:
                order._send_booked_email()
        if vals.get("x_state_custom") == "complete":
            for order in self:
                order.with_context(
                completion_email=True
            )._send_completion_email()
        return res

    def _send_completion_email(self):
        template = self.env.ref('custom_sale_order.email_template_sale_order_complete')
        for order in self:
            if not order.partner_id:
                raise UserError(_('Kindly Select a Case Manager!'))
            if order.partner_id.email:
                mail = template.send_mail(order.id, force_send=True)

                # Get the created mail.message
                mail_message = self.env['mail.mail'].browse(mail).mail_message_id

                self.partner_id.message_post(
                    body=mail_message.body,
                    subject=mail_message.subject,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
                self.client_id.message_post(
                    body=mail_message.body,
                    subject=mail_message.subject,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
            else:
                raise UserError(_('Case Manager Do not have an email address.!'))
            
    def _send_booked_email(self):
        template = self.env.ref('custom_sale_order.email_template_sale_order_booked')
        for order in self:
            if not order.partner_id:
                raise UserError(_('Kindly Select a Case Manager!'))
            if order.partner_id.email:
                mail = template.send_mail(order.id, force_send=True)

                 # Get the created mail.message
                mail_message = self.env['mail.mail'].browse(mail).mail_message_id

                self.partner_id.message_post(
                    body=mail_message.body,
                    subject=mail_message.subject,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
                self.client_id.message_post(
                    body=mail_message.body,
                    subject=mail_message.subject,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )

            else:
                raise UserError(_('Case Manager Do not have an email address.!'))

    def _create_project_task_for_order(self, note_text=None):
        # partner = self.partner_shipping_id
        partner = self.client_id
        if partner:
            client_parts = [partner.name, partner.street, partner.city, partner.phone]
            client_details = ", ".join([part for part in client_parts if part])
        else:
            client_details = ''

        # Create Project with note as description if provided

        tasktypes = self.env['project.task.type'].sudo().search([('is_custom_task_type','=',True)])

        html_paragraph = Markup(
            "<p>"
            "Project for Sale Order: <strong>{sale_order}</strong>.<br/>"
            "Client Name: <strong>{client_name}</strong>.<br/>"
            "Provider Name: <strong>{provider_name}</strong><br/>"
            "Case Manager Name: <strong>{casemanager_name}</strong><br/>"
            "<strong>Note:</strong><br/>"
            "To Open The Task, of this project use the above smart button named -> <strong>Tasks</strong>."
            "</p>"
        ).format(sale_order=self.display_name, client_name=self.client_id.name, provider_name=self.provider_id.name, casemanager_name=self.partner_id.name)

        project = self.env['project.project'].create({
            'name': f"Project {self.name}",
            'partner_id':self.client_id.id,
            'sale_order_ref': self.id,
            'is_fsm':True,
            'company_id': self.env.company.id,
            'type_ids': [Command.link(tasktype.id) for tasktype in tasktypes],
            'date_start': fields.Datetime.now(),
            'date': fields.Datetime.now() + timedelta(hours=8),  # Start = now,
            'description':html_paragraph,
        })

        # <field name="type_ids" eval="[(4, ref('planning_project_stage_0')), (4, ref('planning_project_stage_1')), (4, ref('planning_project_stage_2')), (4, ref('planning_project_stage_3')), (4, ref('planning_project_stage_4'))]"/>
        self.project_id = project
        task = self.env['project.task'].create({
            'name': client_details,
            'partner_id': self.client_id.id,
            'sale_order_ref': self.id,
            'project_id': project.id,
            'sale_description': note_text or '',
            'planned_date_begin': fields.Datetime.now(),  # Start = now
            'date_deadline': fields.Datetime.now() + timedelta(hours=8),  # Deadline = +8 hours
            'provider_id':self.provider_id.id,
        })
        self.task_id = task



    # Remove the note (terms and conditions) so it does not carry over to the invoice
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.pop('narration', None)
        # Add client photos from sale order to invoice
        if self.client_photo_ids:
            invoice_vals['client_photo_ids'] = [(6, 0, self.client_photo_ids.ids)]
        return invoice_vals

    def action_confirm(self):
        for order in self:
            if not order.order_line:
                raise UserError("You must add at least one line before confirming the sale order.")

            first_line = order.order_line[0]
            if first_line.display_type != 'line_note':
                raise UserError("The first line of the sale order must be a Note.")

            note_text = first_line.name

            res = super(SaleOrder, order).action_confirm()

            # Create project with the note
            if not order.project_id:
                order._create_project_task_for_order(note_text=note_text)

        return res

    def action_open_task_calendar(self):
        """Open calendar view for the related task activities"""
        return {
            "type": "ir.actions.act_window",
            "name": f"Calendar for {self.task_id.display_name}",
            "res_model": "project.task",
            "view_mode": "calendar,list,form",
            "context": {
                "search_default_project_id": self.project_id.id,  # filter by project
                "initial_date": self.task_id.planned_date_begin,
            },
        }
    
    def action_open_project(self):
        """Open project view"""
        return {
            "type": "ir.actions.act_window",
            "name": f"Project for {self.display_name}",
            "res_model": "project.project",
            "res_id": self.project_id.id,
            "view_mode": "form",
        }

    def _find_mail_template(self):
        """ Get the appropriate mail template for the current sales order based on its state.

        If the SO is confirmed, we return the mail template for the sale confirmation.
        Otherwise, we return the quotation email template.

        :return: The correct mail template based on the current status
        :rtype: record of `mail.template` or `None` if not found
        """
        self.ensure_one()
        if self.env.context.get('proforma') or self.state != 'sale':
            return self.env.ref('custom_sale_order.email_template_edi_salex', raise_if_not_found=False)
        else:
            return self._get_confirmation_template()

    def _get_confirmation_template(self):
        """ Get the mail template sent on SO confirmation (or for confirmed SO's).

        :return: `mail.template` record or None if default template wasn't found
        """
        self.ensure_one()
        return self.env.ref('custom_sale_order.mail_template_sale_confirmation', raise_if_not_found=False)
    

    def swap_partner_id_and_partner_shipping_id(self):
        for record in self:
            _logger.info('Swaping For %s has started', record.name)
            partner_obj = record.partner_id
            partner_shipping_obj = record.partner_shipping_id
            partner_invoice_obj = record.partner_invoice_id
            _logger.info('Before Swapped Partner_Id --> %s  Shipping Id --> %s', record.partner_id.display_name,record.partner_shipping_id.display_name)
            record.sudo().write(
                {
                    'partner_id': partner_shipping_obj.id,
                    'partner_shipping_id': partner_obj.id,
                    'provider_id': partner_invoice_obj.id,
                    'case_manager_id': partner_obj.id
                }
            )
            _logger.info('Swapped Partner_Id --> %s  Shipping Id --> %s', record.partner_id.display_name,record.partner_shipping_id.display_name)
    
    def set_shipping_id(self):
        for record in self:
            partner_obj = record.partner_id
            record.sudo().write(
                {
                    'partner_shipping_id':partner_obj.id
                }
            )
    
    def fix_fields(self):
        # Swaps Partner and Case Manager
        for record in self:
            partner_id_obj = record.partner_id  # Currently the client.
            case_manager_obj = record.case_manager_id

            record.sudo().write({
                'partner_id': case_manager_obj.id,
                'client_id': partner_id_obj.id
            }
            )
    
        # INVOICING #
        # To Create invoice for the Provider Field
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()

        txs_to_be_linked = self.transaction_ids.sudo().filtered(
            lambda tx: (
                tx.state in ('pending', 'authorized')
                or tx.state == 'done' and not (tx.payment_id and tx.payment_id.is_reconciled)
            )
        )

        values = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.provider_id.id,
            'partner_shipping_id': self.client_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(self.provider_id)).id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_user_id': self.user_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [Command.set(txs_to_be_linked.ids)],
            'company_id': self.company_id.id,
            'invoice_line_ids': [],
            'user_id': self.user_id.id,
        }
        if self.journal_id:
            values['journal_id'] = self.journal_id.id
        return values
    

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_so_as_sent'):
            # Send mail to partner too
            if self.partner_id:
                self.partner_id.message_post(
                    body=kwargs['body'],
                    subject=kwargs['subject'],
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
            if self.client_id:
                self.client_id.message_post(
                    body=kwargs['body'],
                    subject=kwargs['subject'],
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
            self.filtered(lambda o: o.state == 'draft').with_context(tracking_disable=True).write({'state': 'sent'})
        so_ctx = {'mail_post_autofollow': self.env.context.get('mail_post_autofollow', True)}
        if self.env.context.get('mark_so_as_sent') and 'mail_notify_author' not in kwargs:
            kwargs['notify_author'] = self.env.user.partner_id.id in (kwargs.get('partner_ids') or [])
        
        
        return super(SaleOrder, self.with_context(**so_ctx)).message_post(**kwargs)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        template = self.env.ref('custom_sale_order.email_template_invoice_confirmation')
        _logger.info(f"name of the template {template}")
        sale_orders = self.sale_order_ids
        for order in sale_orders:
            _logger.info(f"sale order name  {order.name}")
            if not order.partner_id:
                raise UserError(_('Kindly Select a Case Manager!'))
            if order.partner_id.email:
                _logger.info(f"sale order name  {order.partner_id.email}")
                mail = template.send_mail(order.id, force_send=True)

                 # Get the created mail.message
                mail_message = self.env['mail.mail'].browse(mail).mail_message_id

                order.partner_id.message_post(
                    body=mail_message.body,
                    subject=mail_message.subject,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
                order.client_id.message_post(
                    body=mail_message.body,
                    subject=mail_message.subject,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
            else:
                raise UserError(_('Case Manager Do not have an email address.!'))

                _logger.info(f"email sent ")
        return super(SaleAdvancePaymentInv, self).create_invoices()

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _timesheet_service_generation(self):
        """ For service lines, create the task or the project. If already exists, it simply links
            the existing one to the line.
            Note: If the SO was confirmed, cancelled, set to draft then confirmed, avoid creating a
            new project/task. This explains the searches on 'sale_line_id' on project/task. This also
            implied if so line of generated task has been modified, we may regenerate it.
        """
        if self.env.context.get('no_project_create'):
            return
        so_line_task_global_project = self._get_so_lines_task_global_project()
        so_line_new_project = self._get_so_lines_new_project()

        # search so lines from SO of current so lines having their project generated, in order to check if the current one can
        # create its own project, or reuse the one of its order.
        map_so_project = {}
        if so_line_new_project:
            order_ids = self.mapped('order_id').ids
            so_lines_with_project = self.search([('order_id', 'in', order_ids), ('project_id', '!=', False), ('product_id.service_tracking', 'in', ['project_only', 'task_in_project']), ('product_id.project_template_id', '=', False)])
            map_so_project = {sol.order_id.id: sol.project_id for sol in so_lines_with_project}
            so_lines_with_project_templates = self.search([('order_id', 'in', order_ids), ('project_id', '!=', False), ('product_id.service_tracking', 'in', ['project_only', 'task_in_project']), ('product_id.project_template_id', '!=', False)])
            map_so_project_templates = {(sol.order_id.id, sol.product_id.project_template_id.id): sol.project_id for sol in so_lines_with_project_templates}

        # search the global project of current SO lines, in which create their task
        map_sol_project = {}
        if so_line_task_global_project:
            map_sol_project = {sol.id: sol.product_id.with_company(sol.company_id).project_id for sol in so_line_task_global_project}

        def _can_create_project(sol):
            if not sol.project_id:
                if sol.product_id.project_template_id:
                    return (sol.order_id.id, sol.product_id.project_template_id.id) not in map_so_project_templates
                elif sol.order_id.id not in map_so_project:
                    return True
            return False

        # we store the reference analytic account per SO
        map_account_per_so = {}

        # project_only, task_in_project: create a new project, based or not on a template (1 per SO). May be create a task too.
        # if 'task_in_project' and project_id configured on SO, use that one instead
        for so_line in so_line_new_project.sorted(lambda sol: (sol.sequence, sol.id)):
            project = False
            if so_line.product_id.service_tracking in ['project_only', 'task_in_project']:
                project = so_line.project_id
            if not project and _can_create_project(so_line):
                project = so_line._timesheet_create_project()

                # If the SO generates projects on confirmation and the project's SO is not set, set it to the project's SOL with the lowest (sequence, id)
                if not so_line.order_id.project_id:
                    so_line.order_id.project_id = project
                # If no reference analytic account exists, set the account of the generated project to the account of the project's SO or create a new one
                account = map_account_per_so.get(so_line.order_id.id)
                if not account:
                    account = so_line.order_id.project_account_id or self.env['account.analytic.account'].create(so_line.order_id._prepare_analytic_account_data())
                    map_account_per_so[so_line.order_id.id] = account
                project.account_id = account

                if so_line.product_id.project_template_id:
                    map_so_project_templates[(so_line.order_id.id, so_line.product_id.project_template_id.id)] = project
                else:
                    map_so_project[so_line.order_id.id] = project
            elif not project:
                # Attach subsequent SO lines to the created project
                so_line.project_id = (
                    map_so_project_templates.get((so_line.order_id.id, so_line.product_id.project_template_id.id))
                    or map_so_project.get(so_line.order_id.id)
                )
            if so_line.product_id.service_tracking == 'task_in_project':
                if not project:
                    if so_line.product_id.project_template_id:
                        project = map_so_project_templates[(so_line.order_id.id, so_line.product_id.project_template_id.id)]
                    else:
                        project = map_so_project[so_line.order_id.id]
                if not so_line.task_id:
                    so_line._timesheet_create_task(project=project)
            so_line._handle_milestones(project)

        # task_global_project: if not set, set the project's SO by looking at global projects
        for so_line in so_line_task_global_project.sorted(lambda sol: (sol.sequence, sol.id)):
            if not so_line.order_id.project_id:
                so_line.order_id.project_id = map_sol_project.get(so_line.id)

        # task_global_project: create task in global projects
        for so_line in so_line_task_global_project:
            if not so_line.task_id:
                project = map_sol_project.get(so_line.id) or so_line.order_id.project_id
                if project and so_line.product_uom_qty > 0:
                    so_line._timesheet_create_task(project)
                elif not project:
                    raise UserError(_(
                        "A project must be defined on the quotation %(order)s or on the form of products creating a task on order.\n"
                        "The following product need a project in which to put its task: %(product_name)s",
                        order=so_line.order_id.name,
                        product_name=so_line.product_id.name,
                    ))
