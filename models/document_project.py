from odoo import api, fields, models, _


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
    ], string='Status', compute='_compute_state', store=True)

    quantity = fields.Integer(string='Quantity', compute='get_quantity_remaining', store=True)
    remaining = fields.Integer(string='Actually', compute='get_quantity_remaining', store=True)
    meta_project_ids = fields.One2many('meta.projects', 'project_id')

    @api.depends('meta_project_ids')
    def get_quantity_remaining(self):
        for project in self:
            project.quantity = len(project.meta_project_ids)
            project.remaining = len(project.meta_project_ids.filtered(
                lambda a: a.state == 'available'
            ))

    @api.depends('remaining')
    def _compute_state(self):
        for project in self:
            project.state = 'available' if project.remaining > 0 else 'not_available'

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


class MetaProject(models.Model):
    _name = 'meta.projects'
    _description = 'Meta Project'

    project_id = fields.Many2one('document.project', string='Project')
    name_seq = fields.Char(string="Meta Project ID", default=lambda self: _('New'), readonly=True)
    description = fields.Text('Description')
    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', default='available')

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s' %
                        (rec.name_seq)))
        return res

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('library.meta.magazine.newspaper.sequence') or _(
                'New')
        result = super(MetaProject, self).create(vals)
        return result
