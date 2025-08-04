# -*- coding: utf-8 -*-
{
    'name': 'Xero Integration OAuth 2.0 REST API',
    'version': '4.6',
    'category': 'Services',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': "www.pragtech.co.in",
    'depends': ['account', 'sale_management', 'base', 'purchase'],
    'summary': 'Xero Connector with REST API Xero Odoo Integration App xero accounting odoo xero connector odoo xero integration odoo xero accounting integration accounting app',
    'description': """
Xero Connector with REST API
============================
<keywords>
Xero Odoo Integration App
xero
xero odoo 
xero accounting
odoo xero connector
odoo xero integration
odoo xero accounting integration
accounting app
""",
    'data': [
        'views/res_company.xml',
        'views/account_account.xml',
        'views/tax.xml',
        'views/product_template.xml',
        'views/res_partner_category.xml',
        'wizard/connection_successfull_view.xml',
        'views/purchase_order.xml',
        'views/invoice.xml',
        'views/res_partner.xml',
        'views/account_payments.xml',
        'views/maintain_logs.xml',
        'views/sale_order.xml',
        'views/dashboard.xml',
        'views/xero_logger_view.xml',
        'views/automated_authentication_scheduler.xml',
        'security/ir.model.access.csv',
        'data/type_demo_data.xml',
    ],
    'images': ['static/description/odoo-xero-connector-gif.gif'],
    'live_test_url': 'http://www.pragtech.co.in/company/proposal-form.html?id=103&name=Odoo-xero-Accounting-Management',
    'license': 'OPL-1',
    'price': 299.00,
    'currency': 'USD',
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'pragmatic_odoo_xero_connector/static/src/js/dashboard.js',
            'pragmatic_odoo_xero_connector/static/src/css/xero.css',
            'https://www.gstatic.com/charts/loader.js',
            'pragmatic_odoo_xero_connector/static/src/xml/dashboard.xml',
            'web/static/lib/jquery/jquery.js',
        ],
    },
}
