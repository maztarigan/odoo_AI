# -*- coding: utf-8 -*-
import json
import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ModelAIPrompt(models.Model):
    _name = 'model.ai.prompt'
    _description = 'ChatGPT Prompt'

    name = fields.Char(string='Title', required=True, default=lambda self: _('New Prompt'))
    prompt = fields.Text(string='Prompt', required=True)
    response = fields.Text(string='Response', readonly=True)
    model_name = fields.Char(string='Model', default='gpt-3.5-turbo')
    temperature = fields.Float(string='Temperature', default=0.2)
    max_tokens = fields.Integer(string='Max Tokens', default=256)

    def action_send_prompt(self):
        for record in self:
            record._send_prompt_to_openai()

    def _send_prompt_to_openai(self):
        self.ensure_one()
        api_key = self.env['ir.config_parameter'].sudo().get_param('model_ai.openai_api_key')
        if not api_key:
            raise UserError(
                _('Please configure the OpenAI API key in System Parameters with the key "model_ai.openai_api_key".')
            )

        payload = {
            'model': self.model_name or 'gpt-3.5-turbo',
            'messages': [
                {
                    'role': 'user',
                    'content': self.prompt,
                }
            ],
            'temperature': self.temperature,
            'max_tokens': self.max_tokens or 256,
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        }

        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                data=json.dumps(payload),
                timeout=60,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            _logger.exception('OpenAI API HTTP error: %s', exc)
            raise UserError(_('OpenAI API returned an error: %s') % exc.response.text)
        except requests.RequestException as exc:
            _logger.exception('OpenAI API request error: %s', exc)
            raise UserError(_('Could not reach OpenAI API: %s') % exc)

        data = response.json()
        try:
            message = data['choices'][0]['message']['content']
        except (KeyError, IndexError) as exc:
            _logger.exception('Unexpected OpenAI API response: %s', data)
            raise UserError(_('Unexpected response format from OpenAI: %s') % exc)

        self.write({'response': message})
        return True
