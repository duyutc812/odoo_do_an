from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Project(models.Model):
    _name = 'lib.document.project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Đồ án - luận văn'

    name = fields.Char('Tên đồ án', required=True, track_visibility='always')
    major_id = fields.Many2one('lib.student.major', string='Chuyên ngành', requied=True, track_visibility='always')
    student_id = fields.Many2one('lib.student', string='Mã sinh viên', track_visibility='always')
    student_name = fields.Char('Tên sinh viên', related='student_id.name', store=True, track_visibility='always')
    course = fields.Integer('Khoá học', related='student_id.course', store=True, track_visibility='always')
    teacher_id = fields.Many2one('lib.teacher', string='Giảng viên HD')
    publish_date = fields.Date('Ngày thực hiện', track_visibility='always')
    rack = fields.Many2one('lib.rack', 'Giá chứa', track_visibility='always')
    project_term = fields.Integer('Giới hạn mượn(ngày)', default=15)
    currency_id = fields.Many2one('res.currency', 'Tiền tệ',
                                  default=lambda s: s.env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1)
                                  )
    price = fields.Monetary('Giá tiền', 'currency_id', track_visibility='always')
    quantity = fields.Integer(string='Số lượng', compute='_compute_quantity_remaining', store=True)
    remaining = fields.Integer(string='Còn lại', compute='_compute_quantity_remaining', store=True)
    state = fields.Selection([
        ('available', 'Có sẵn'),
        ('not_available', 'Không có sẵn')
    ], string='Trạng thái', compute='_compute_quantity_remaining', store=True)
    # , compute='_compute_state', store=True
    meta_project_ids = fields.One2many('lib.meta.projects', 'project_id')

    @api.constrains('project_term')
    def _constrains_price(self):
        for pro in self:
            if pro.project_term <= 0:
                raise ValidationError(_("Giới hạn ngày mượn phải lớn hơn 0!"))

    def unlink(self):
        for doc_pr in self:
            if len(doc_pr.meta_project_ids):
                raise ValidationError(_('Bạn không thể xoá khi meta đồ án còn tồn tại!'))
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
         'Ngày thực hiện phải nhỏ hơn hoặc bằng ngày hiện tại!'),
    ]

    @api.onchange('major_id')
    def _onchange_student_major_id(self):
        self.student_id = ''
        return {'domain': {'student_id': [('major_id', '=', self.major_id.id)]}}


class MetaProject(models.Model):
    _name = 'lib.meta.projects'
    _description = 'Meta đồ án - luận văn'

    name_seq = fields.Char(string="Mã meta Đồ án/luận văn", default=lambda self: _('New'), readonly=True)
    project_id = fields.Many2one('lib.document.project', string='Đồ án - luận văn')
    description = fields.Text('Tình trạng', default='Tài liệu mới')
    state = fields.Selection([
        ('available', 'Có sẵn'),
        ('not_available', 'Không có sẵn')
    ], string='Status', default='available')
    sequence = fields.Integer()
    checkout = fields.Char('Phiếu mượn')
    is_lost = fields.Boolean('Đã mất', default=False)
    is_active = fields.Boolean('Có hiệu lực', default=True)

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
                raise ValidationError(_('Bạn không thể xoá :%s khi meta đồ án còn tồn taij trong phiếu mượn!' % (pro.name_seq)))
        return super(MetaProject, self).unlink()
