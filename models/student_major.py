from odoo import api, fields, models


class Major(models.Model):
    _name = 'student.major'
    _description = 'Student Major'
    _rec_name = 'name'

    name = fields.Char('Major')