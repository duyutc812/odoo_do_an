from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Project(models.Model):
    _name = 'lib.document.project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Document - Project'

    name = fields.Char('Name Project', required=True, track_visibility='always')
    major_id = fields.Many2one('lib.student.major', string='Major', requied=True, track_visibility='always')
    student_id = fields.Many2one('lib.student', string='Student ID', track_visibility='always')
    student_name = fields.Char('Name Student', related='student_id.name', store=True, track_visibility='always')
    course = fields.Integer('Course', related='student_id.course', store=True, track_visibility='always')
    teacher_id = fields.Many2one('lib.teacher', string='Tutorial Teacher ')
    publish_date = fields.Date('Publish Date', track_visibility='always')
    rack = fields.Many2one('lib.rack', 'Rack', track_visibility='always')
    project_term = fields.Integer('Project Term (Days)', default=15)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda s: s.env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1)
                                  )
    price = fields.Monetary('Price', 'currency_id', track_visibility='always')
    quantity = fields.Integer(string='Quantity', compute='_compute_quantity_remaining', store=True)
    remaining = fields.Integer(string='Remaining', compute='_compute_quantity_remaining', store=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', compute='_compute_quantity_remaining', store=True)
    # , compute='_compute_state', store=True
    meta_project_ids = fields.One2many('lib.meta.projects', 'project_id')

    @api.constrains('project_term')
    def _constrains_price(self):
        for pro in self:
            if pro.project_term <= 0:
                raise ValidationError(_("The project term must be greater than 0!"))

    def unlink(self):
        for doc_pr in self:
            if len(doc_pr.meta_project_ids):
                raise ValidationError(_('You cannot delete!'))
        return super(Project, self).unlink()

    @api.multi
    @api.depends('meta_project_ids')
    def _compute_quantity_remaining(self):
        for project in self:
            project.quantity = len(project.meta_project_ids)
            project.remaining = len(project.meta_project_ids.filtered(
                lambda a: a.state == 'available'
            ))
            # print('depends')
            project.state = 'not_available'
            if project.remaining > 0:
                project.state = 'available'

    # @api.depends('remaining')
    # def _compute_state(self):
    #     for project in self:
    #         project.state = 'available' if project.remaining > 0 else 'not_available'

    _sql_constraints = [
        ('document_project_publish_date_chk',
         'CHECK (publish_date <= current_date)',
         'Publish date must not be in the future!'),
    ]

    @api.onchange('major_id')
    def _onchange_student_major_id(self):
        self.student_id = ''
        return {'domain': {'student_id': [('major_id', '=', self.major_id.id)]}}


class MetaProject(models.Model):
    _name = 'lib.meta.projects'
    _description = 'Meta Project'

    name_seq = fields.Char(string="Meta Project ID", default=lambda self: _('New'), readonly=True)
    project_id = fields.Many2one('lib.document.project', string='Project')
    description = fields.Text('Description', default='Tài liệu mới')
    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', default='available')
    sequence = fields.Integer()
    checkout = fields.Char()
    is_lost = fields.Boolean('Lost', default=False)
    is_active = fields.Boolean('Active', default=True)

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s' % (rec.name_seq)))
        return res

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('lib.meta.document.project.sequence') or _(
                'New')
        result = super(MetaProject, self).create(vals)
        return result

    def unlink(self):
        for pro in self:
            if pro.checkout:
                raise ValidationError(_('You cannot delete record %s!' % (pro.name_seq)))
        return super(MetaProject, self).unlink()
