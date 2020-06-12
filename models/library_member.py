from odoo import api, fields, models
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

    address = fields.Text('Address')
    facebook = fields.Char('Facebook')


class Student(models.Model):
    _name = 'library.student'
    _description = 'Student'
    _rec_name = 'name'

    @api.model
    def _default_major(self):
        return self.env['student.major'].search([], limit=1)

    name = fields.Char('Name', required=True)
    student_image = fields.Binary('Cover', default=get_default_img())
    student_id = fields.Char('Student ID', required=True)
    identity_card = fields.Char('Identity Card')
    born_date = fields.Date('Born Date', default=fields.Date.today())
    age = fields.Integer('Age', compute='_compute_age', store=True, readonly=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], default='male', string="Gender")
    address = fields.Text('Address')
    phone = fields.Char('Phone')
    email = fields.Char('Email')
    facebook = fields.Char('Facebook')
    major = fields.Many2one('student.major', string="Major", default=_default_major)
    course = fields.Integer('Course', default=57)
    note = fields.Html('Notes')
    country_id = fields.Many2one('res.country', 'Nationality')
    active = fields.Boolean('Active?', default=True)
    color = fields.Integer('Color')
    count = fields.Integer('Count', compute='_compute_student_card')

    def _compute_student_card(self):
        domain = [('student_id', '=', self.id), ('state', '=', 'running')]
        self.count = self.env['library.card'].search_count(domain)

    @api.multi
    def name_get(self):
        res = []
        for student in self:
            res.append((student.id, '%s - %s - %s%s' % (student.name, student.student_id, 'K', student.course)))
        return res

    @api.depends('born_date')
    def _compute_age(self):
        """Method to onchange birth_date for student"""
        curr_date = fields.Date.today()
        for student in self:
            born_date = student.born_date
            student.age = curr_date.year - born_date.year - \
                      ((curr_date.month, curr_date.day) <
                       (born_date.month, born_date.day)) if born_date else 0
            if student.age < 0:
                student.age = 0

    @api.onchange('name')
    def _onchange_name_upper(self):
        """Method to set upper for name"""
        for student in self:
            student.name = student.name.title() if student.name else ''

    _sql_constraints = [
        ('student_id_unique',
         'unique(student_id)',
         'The Student ID must be unique.'
         ),
        ('identity_card_unique',
         'unique(identity_card)',
         'The Identity Card must be unique.'
         ),
        ('email_unique',
         'unique(email)',
         'The Email must be unique.'
         )
    ]


class Teacher(models.Model):
    _name = 'library.teacher'
    _description = 'Teacher'
    _rec_name = 'name'

    name = fields.Char('Name')
    teacher_image = fields.Binary('Cover', default=get_default_img())
    born_date = fields.Date('Born Date')
    address = fields.Text('Address')
    age = fields.Integer('Age')
    gender = fields.Selection([
        ('male', 'Male'),
        ('fe_male', 'Female')
    ])
    phone = fields.Char('Phone')
    email = fields.Char('Email Contact')
    role = fields.Many2one('teacher.role', string='Role')
    note = fields.Html('Notes')
    country_id = fields.Many2one('res.country', 'Nationality')
    active = fields.Boolean('Active?', default=True)
    # user_id = fields.Many2one('res.users', string='User', default=lambda self: self._uid)

    @api.onchange('born_date')
    def _onchange_born_date(self):
        """Method to set upper for name"""
        curr_date = fields.Date.today()
        for teacher in self:
            born_date = teacher.born_date
            teacher.age = curr_date.year - born_date.year -\
                          ((curr_date.month, curr_date.day) < (born_date.month, born_date.day))\
                if born_date else ''

    @api.onchange('name')
    def _onchange_name_upper(self):
        """Method to set upper for name"""
        for teacher in self:
            teacher.name = teacher.name.title() if teacher.name else ''










