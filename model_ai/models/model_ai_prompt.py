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
    nomor_spk = fields.Char(string='Nomor SPK')
    customer_complaint = fields.Text(string='Keluhan Pelanggan')
    response = fields.Text(string='Response', readonly=True)
    fishbone_analysis_image = fields.Binary(string='Fishbone Analysis Image', readonly=True)
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

        content = self._compose_prompt_content()

        payload = {
            'model': self.model_name or 'gpt-3.5-turbo',
            'messages': [
                {
                    'role': 'user',
                    'content': content,
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

        updates = {'response': message}

        fishbone_image = self._generate_fishbone_image(message)
        if fishbone_image:
            updates['fishbone_analysis_image'] = fishbone_image

        self.write(updates)
        return True

    def _compose_prompt_content(self):
        self.ensure_one()

        sections = [_('Buatkan analisis dan rencana tindakan CAPA berdasarkan data berikut.')]
        if self.prompt:
            sections.append(self.prompt.strip())
        context_lines = []
        if self.nomor_spk and self.nomor_spk.strip():
            context_lines.append(_('Nomor SPK: %s') % self.nomor_spk.strip())
        if self.customer_complaint and self.customer_complaint.strip():
            context_lines.append(_('Keluhan Pelanggan: %s') % self.customer_complaint.strip())

        if context_lines:
            sections.append(_('Informasi Konteks:'))
            sections.append('\n'.join(context_lines))

        return '\n\n'.join(filter(None, sections))

    def _generate_fishbone_image(self, analysis_text):
        api_key = self.env['ir.config_parameter'].sudo().get_param('model_ai.openai_api_key')
        if not api_key:
            return False

        prompt = _(
            'Create a detailed fishbone (Ishikawa) diagram that visualizes the root cause analysis for the following case:\n%s'
        ) % (analysis_text or '')

        payload = {
            'model': 'gpt-image-1',
            'prompt': prompt,
            'size': '1024x1024',
            'response_format': 'b64_json',
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        }

        try:
            response = requests.post(
                'https://api.openai.com/v1/images/generations',
                headers=headers,
                data=json.dumps(payload),
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            _logger.warning('Failed to generate fishbone analysis image: %s', exc)
            return False

        try:
            data = response.json()
            image_base64 = data['data'][0]['b64_json']
        except (KeyError, IndexError, ValueError) as exc:
            _logger.warning('Unexpected OpenAI image generation response: %s', exc)
            return False

        return image_base64
