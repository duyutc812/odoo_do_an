from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryDuration(models.Model):
    _name = 'library.duration'
    _description = 'Library Duration'

    name = fields.Char('Name', readonly=True, compute='_compute_name', store=True)
    duration = fields.Integer('Duration(month)', required=True)
    user_type = fields.Selection([
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ], string='User Type', default='student')
    book_on_card = fields.Integer('No book on card', required=True)
    syllabus_on_card = fields.Integer('No syllabus on card', required=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda s: s.env['res.currency'].search([('name', '=', 'VND')], limit=1))
    price = fields.Monetary('Price', 'currency_id')

    @api.depends('duration', 'user_type')
    def _compute_name(self):
        for lib_dur in self:
            lib_dur.name = str(lib_dur.duration) + (' months' if lib_dur.duration > 1 else 'month') \
                           + '(' + str(lib_dur.user_type) + ')'

    @api.constrains('duration')
    def _constrains_duration(self):
        if self.duration <= 0:
            raise ValidationError('Duration must be great 0!')

    _sql_constraints = [
        ('duration_user_uniq',
         'unique (duration, user_type)',
         'The duration and user type must be unique !'),
    ]

