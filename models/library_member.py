from odoo import api, fields, models, _
from datetime import date
import time
from .library_author import get_default_img
from odoo.exceptions import ValidationError
import pytz
from odoo import modules
import base64

"""Method to get default_image"""
def get_default_img():
    with open(modules.get_module_resource('do_an_tn', 'static/', 'default_image.png'),
              'rb') as f:
        return base64.b64encode(f.read())


class Employee(models.Model):
    _inherit = 'res.users'

    born_date = fields.Date('Ngày sinh')
    address = fields.Text('Địa chỉ')
    facebook = fields.Char('Facebook')
    email = fields.Char('Email')


class Student(models.Model):
    _name = 'lib.student'
    _description = 'Sinh viên'

    @api.model
    def _default_major(self):
        return self.env['lib.student.major'].search([], limit=1)

    name = fields.Char('Họ tên', required=True)
    student_image = fields.Binary('Ảnh đại diện', default=get_default_img())
    student_id = fields.Char('Mã sinh viên', required=True)
    identity_card = fields.Char('Số CMND')
    born_date = fields.Date('Ngày sinh', default=fields.Date.today())
    gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
    ], default='male', string="Giới tính")
    phone = fields.Char('Số điện thoại')
    email = fields.Char('Email')
    facebook = fields.Char('Facebook')
    street = fields.Char('Đường')
    sub_district = fields.Char('Thị trấn/Xã')
    district = fields.Char('Huyện')
    city = fields.Char('Thành Phố')
    country_id = fields.Many2one('res.country', 'Quốc tịch', default=lambda s: s.env['res.country'].search([('code', '=', 'VN')], limit=1))
    major_id = fields.Many2one('lib.student.major', string="Chuyên Ngành", default=_default_major)
    major_name = fields.Char(related='major_id.name', string='Tên chuyên ngành', readonly=True, store=True)
    course = fields.Integer('Khoá học', default=57)
    note = fields.Text('Note')
    is_active = fields.Boolean('Có hiệu lực', default=True)
    color = fields.Integer('Color')
    count = fields.Integer('Count', compute='_compute_student_card')

    @api.multi
    def _compute_student_card(self):
        domain = [('student_id', '=', self.id), ('state', '=', 'running')]
        self.count = self.env['lib.card'].sudo().search_count(domain)

    @api.multi
    def name_get(self):
        res = []
        for student in self:
            res.append((student.id, '%s - %s - %s%s' % (student.name, student.student_id, 'K', student.course)))
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|', '|', '|', '|', '|', ('name', operator, name),
                         ('email', operator, name),
                         ('student_id', operator, name),
                         ('identity_card', operator, name),
                         ('phone', operator, name),
                         ('major_name', operator, name)]
        return super(Student, self).search(domain, limit=limit).name_get()

    # @api.depends('born_date')
    # def _compute_age(self):
    #     curr_date = fields.Date.today()
    #     for student in self:
    #         born_date = student.born_date
    #         student.age = curr_date.year - born_date.year - \
    #                   ((curr_date.month, curr_date.day) <
    #                    (born_date.month, born_date.day)) if born_date else 0
    #         if student.age < 0:
    #             student.age = 0

    @api.onchange('name')
    def _onchange_name_upper(self):
        self.name = self.name.title() if self.name else ''

    _sql_constraints = [
        ('student_id_unique',
         'unique(student_id)',
         'Mã sinh viên đã tồn tại!'
         ),
        ('identity_card_unique',
         'unique(identity_card)',
         'Số chứng minh nhân dân đã tồn tại!'
         ),
        ('email_unique',
         'unique(email)',
         'Địa chỉ email đã tồn tại!'
         )
    ]

    def unlink(self):
        for stu in self:
            card_id = self.env['lib.card'].search([
                ('student_id', '=', stu.id)
            ])
            # print(check_author_book)
            if card_id:
                raise ValidationError(_('Không thể xoá sinh viên khi thẻ thư viện còn tồn tại!'))
        return super(Student, self).unlink()


class Teacher(models.Model):
    _name = 'lib.teacher'
    _description = 'Giảng viên'

    name = fields.Char('Họ tên')
    teacher_image = fields.Binary('Ảnh', default=get_default_img())
    born_date = fields.Date('Ngày sinh')
    address = fields.Text('Địa chỉ')
    gender = fields.Selection([
        ('male', 'Nam'),
        ('fe_male', 'Nữ')
    ])
    phone = fields.Char('Số điện thoại')
    email = fields.Char('Email liên hệ')
    role = fields.Many2one('lib.teacher.role', string='Chức vụ')
    note = fields.Text('Ghi chú')
    country_id = fields.Many2one('res.country', 'Quốc tịch', default=lambda s: s.env['res.country'].search([('code', '=', 'VN')], limit=1))
    is_active = fields.Boolean('Có hiệu lực?', default=True)
    # user_id = fields.Many2one('res.users', string='User', default=lambda self: self._uid)

    # @api.onchange('born_date')
    # def _onchange_born_date(self):
    #     curr_date = fields.Date.today()
    #     born_date = self.born_date
    #     self.age = curr_date.year - born_date.year -\
    #               ((curr_date.month, curr_date.day) < (born_date.month, born_date.day))\
    #         if born_date else ''

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|', '|', '|', ('name', operator, name),
                         ('email', operator, name),
                         ('role', operator, name),
                         ('phone', operator, name)]
        return super(Teacher, self).search(domain, limit=limit).name_get()

    @api.onchange('name')
    def _onchange_name_upper(self):
        self.name = self.name.title() if self.name else ''

    _sql_constraints = [
        ('email_unique',
         'unique(email)',
         'Email đã tồn tại!'
         )
    ]

    def unlink(self):
        for teacher in self:
            card_id = self.env['lib.card'].search([
                ('teacher_id', '=', teacher.id)
            ])
            # print(check_author_book)
            if card_id:
                raise ValidationError(_('Không thể xoá giảng viên khi thẻ thư viện còn tồn tại!'))
        return super(Teacher, self).unlink()










