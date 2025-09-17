# -*- coding: utf-8 -*-
{
    'name': 'Model AI',
    'version': '14.0.1.0.0',
    'summary': 'Integrate ChatGPT prompts inside Odoo',
    'description': 'Send prompts to OpenAI\'s ChatGPT API and capture the responses.',
    'category': 'Productivity',
    'author': 'ChatGPT',
    'website': 'https://openai.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/model_ai_prompt_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
