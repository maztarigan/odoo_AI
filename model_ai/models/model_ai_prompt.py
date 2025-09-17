# -*- coding: utf-8 -*-
import json
import logging
import re

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
    response_problem_summary = fields.Text(string='Masalah dari Pelanggan', readonly=True)
    response_root_cause = fields.Text(string='Analisa Masalah', readonly=True)
    response_fishbone_summary = fields.Text(string='Fishbone Analysis', readonly=True)
    response_supporting_plan = fields.Text(
        string='Bagian Pendukung (CAPA & Indikator)', readonly=True
    )
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

        sections = self._extract_response_sections(message)
        updates = {'response': message, **sections}

        fishbone_image = self._generate_fishbone_image(message)
        if fishbone_image:
            updates['fishbone_analysis_image'] = fishbone_image

        self.write(updates)
        return True

    def _compose_prompt_content(self):
        self.ensure_one()

        sections = [
            _('Buatkan analisis dan rencana tindakan CAPA berdasarkan data berikut.'),
            _(
                'Susun respons dengan urutan bagian sebagai berikut:\n'
                '1. Masalah dari Pelanggan (ringkas kembali inti keluhan).\n'
                '2. Analisa Masalah (jelaskan analisis akar penyebab secara singkat dan jelas).\n'
                '3. Fishbone Analysis (uraikan visualisasi atau rangkuman diagram sebelum bagian lain).\n'
                'Lanjutkan dengan bagian-bagian pendukung lain seperti rencana tindakan CAPA dan indikator keberhasilan.'
            ),
        ]
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

    def _extract_response_sections(self, message):
        section_defaults = {
            'response_problem_summary': False,
            'response_root_cause': False,
            'response_fishbone_summary': False,
            'response_supporting_plan': False,
        }

        if not message:
            return section_defaults

        pattern = re.compile(
            r'(?:^|\n)\s*(?:\d+\.\s*)?(?P<title>'
            r'Masalah dari Pelanggan|Analisa Masalah|Fishbone Analysis|'
            r'Lanjutkan dengan bagian-bagian pendukung[^\n]*)\s*[:\-]?\s*',
            re.IGNORECASE,
        )

        matches = list(pattern.finditer(message))
        if not matches:
            section_defaults['response_supporting_plan'] = message.strip() or False
            return section_defaults

        def _map_title_to_field(title):
            title = (title or '').lower()
            if 'masalah dari pelanggan' in title:
                return 'response_problem_summary'
            if 'analisa masalah' in title:
                return 'response_root_cause'
            if 'fishbone analysis' in title:
                return 'response_fishbone_summary'
            if 'lanjutkan dengan bagian-bagian pendukung' in title:
                return 'response_supporting_plan'
            return None

        for idx, match in enumerate(matches):
            field_name = _map_title_to_field(match.group('title'))
            if not field_name:
                continue

            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(message)
            content = message[start:end].strip()
            if content:
                section_defaults[field_name] = content

        return section_defaults
