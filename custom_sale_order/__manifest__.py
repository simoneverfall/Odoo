# -*- coding: utf-8 -*-
{
    'name': 'Custom Sale Order',
    'version': '1.0',
    'summary': 'Custom changes to Sale Order',
    'depends': ['sale','project','account','mail','industry_fsm','sale_project','sale_timesheet'],
    'data': [
        'data/mail_template.xml',
        'data/task_stages.xml',
        # 'data/server_action.xml',
        'views/res_partner_extend.xml',
        'views/sale_order_views.xml',
        'views/account_move.xml',
        'views/product_product.xml',
        'views/project_project.xml',
        'views/project_task.xml',
        'views/sale_report_inherit.xml',
        'views/invoice_report_inherit.xml',
        'data/custom_quotation_email_temp.xml'
    ],
    'installable': True,
    'license': 'LGPL-3',
}