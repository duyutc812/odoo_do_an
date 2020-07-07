from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryDuration(models.Model):
    _name = 'lib.duration'
    _description = 'Library Duration'

    name = fields.Char('Name', readonly=True, compute='_compute_name', store=True)
    duration = fields.Integer('Duration(month)', required=True)
    member_type = fields.Selection([
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ], string='Member Type', default='student')
    book_limit = fields.Integer('No book on card', required=True)
    syllabus_limit = fields.Integer('No syllabus on card', required=True)

    currency_id = fields.Many2one('res.currency', 'Currency')
    price = fields.Monetary('Price', 'currency_id')

    @api.depends('duration', 'member_type')
    def _compute_name(self):
        for lib_dur in self:
            lib_dur.name = str(lib_dur.duration) + (' months' if lib_dur.duration > 1 else 'month') \
                           + '(' + str(lib_dur.member_type) + ')'

    @api.constrains('duration')
    def _constrains_duration(self):
        if self.duration <= 0:
            raise ValidationError(_('Duration must be great 0!'))

    _sql_constraints = [
        ('duration_member_type_uniq',
         'unique (duration, member_type)',
         'The duration and member_type must be unique !'),
    ]

