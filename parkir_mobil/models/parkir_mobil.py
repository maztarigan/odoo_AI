# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ParkirMobil(models.Model):
    _name = 'parkir.mobil'
    _description = 'Parkir Mobil'

    tanggal = fields.Date(string='Tanggal', required=True, default=fields.Date.context_today)
    nomor_plat = fields.Char(string='Nomor Plat', required=True)
    jam_masuk = fields.Float(string='Jam Masuk', required=True, help='Format HH:MM')
    jam_keluar = fields.Float(string='Jam Keluar', help='Format HH:MM')
    total_jam = fields.Float(string='Total Jam', compute='_compute_total_jam', store=True)
    tarif = fields.Float(string='Tarif', compute='_compute_tarif', store=True)

    @api.depends('jam_masuk', 'jam_keluar')
    def _compute_total_jam(self):
        for record in self:
            if record.jam_masuk and record.jam_keluar:
                total_hours = record.jam_keluar - record.jam_masuk
                record.total_jam = max(total_hours, 0.0)
            else:
                record.total_jam = 0.0

    @api.depends('total_jam')
    def _compute_tarif(self):
        for record in self:
            record.tarif = record.total_jam * 1000.0
