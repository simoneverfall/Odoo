# -*- coding: utf-8 -*-
{
    'name': 'Custom Sale Order',
    'version': '1.0',
    'summary': 'Custom changes to Sale Order',
    'depends': ['sale','project','account'],
    'data': [
        'views/sale_order_views.xml',
        'views/account_move.xml',
        'views/product_product.xml',
        'views/project_project.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}