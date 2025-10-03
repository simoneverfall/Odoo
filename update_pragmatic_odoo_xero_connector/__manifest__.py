# -*- coding: utf-8 -*-
{
    'name': "update_pragmatic_odoo_xero_connector",

    'summary': "Modifies some features of original module.",

    'description': """
        Custom Development to make things according to client requirement.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Services',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['pragmatic_odoo_xero_connector'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
    ],
    'installable': True,
}

