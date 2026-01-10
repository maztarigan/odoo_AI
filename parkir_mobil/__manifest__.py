# -*- coding: utf-8 -*-
{
    'name': 'Parkir Mobil',
    'version': '18.0.1.0.0',
    'summary': 'Pencatatan parkir mobil berdasarkan tanggal, plat, jam, dan tarif',
    'category': 'Operations',
    'author': 'ChatGPT',
    'website': 'https://openai.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/parkir_mobil_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
