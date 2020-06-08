from odoo import api, fields, models


class TeacherRole(models.Model):
    _name = 'teacher.role'
    _description = 'Teacher Role'

    name = fields.Char('Role')