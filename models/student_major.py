from odoo import api, fields, models


class Major(models.Model):
    _name = 'lib.student.major'
    _description = 'Student Major'

    name = fields.Char('Major')