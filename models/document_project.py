from odoo import api, fields, models


class Project(models.Model):
    _name = 'document.project'
    _description = 'Document - Project'

    name = fields.Char('Name Project', required=True)
    major = fields.Many2one('student.major', string='Major', requied=True)
    student_id = fields.Many2one('library.student', string='Student ID')
    student_name = fields.Char('Name Student', related='student_id.name', store=True)
    course = fields.Integer('Course', related='student_id.course', store=True)
    publish_date = fields.Date('Publish Date')
    teacher_name = fields.Many2one('library.teacher', string='Tutorial Teacher ')

    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', default='available')

    description = fields.Char('Description')

    _sql_constraints = [
        ('document_project_publish_date_chk',
         'CHECK (publish_date <= current_date)',
         'Publish date must not be in the future!'),
    ]

    @api.onchange('major')
    def _onchange_student_major(self):
        for r in self:
            r.student_id = ''
            return {'domain': {'student_id': [('major', '=', r.major.id)]}}


