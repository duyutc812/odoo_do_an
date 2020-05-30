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

    name = fields.Char('Name', required=True)
    student_image = fields.Binary('Cover', default=get_default_img())
    student_id = fields.Char('Student ID', required=True)
    identity_card = fields.Char('Identity Card')
    birth_date = fields.Date('Birth Date', default=fields.Date.today())
    age = fields.Integer('Age', compute='_compute_age', store=True, readonly=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], default='male', string="Gender")
    address = fields.Text('Address')
    phone = fields.Char('Phone')
    email = fields.Char('Email')
    facebook = fields.Char('Facebook')

    @api.model
    def _default_major(self):
        return self.env['student.major'].search([], limit=1)
    major = fields.Many2one('student.major', string="Major", default=_default_major)

    course = fields.Integer('Course', default=57)
    note = fields.Html('Notes')
    country_id = fields.Many2one('res.country', 'Nationality', default=241)
    active = fields.Boolean('Active?', default=True)
    count = fields.Integer('Count', compute='_get_student_card')

    def _get_student_card(self):
        domain = [('student_id', '=', self.id), ('state', '=', 'running')]
        self.count = self.env['library.card'].search_count(domain)

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s - %s - %s%s' % (rec.name, rec.student_id, 'K', rec.course)))
        return res

    @api.depends('birth_date')
    def _compute_age(self):
        """Method to onchange birth_date for student"""
        curr_date = fields.Date.today()
        for rec in self:
            birth_date = rec.birth_date
            rec.age = curr_date.year - birth_date.year - \
                      ((curr_date.month, curr_date.day) <
                       (birth_date.month, birth_date.day)) if birth_date else 0
            if rec.age < 0:
                rec.age = 0
            # if birth_date:
            #     user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)
            #     print('user_tz :', user_tz)
            #     time_in_timezone = pytz.utc.localize(rec.birth_date).astimezone(user_tz)
            #     print(time_in_timezone)

            # date_today = pytz.utc.localize()
            #
            #
            # print(birth_date, curr_date)

    @api.onchange('name')
    def _onchange_and_name_upper(self):
        """Method to set upper for name"""
        for rec in self:
            rec.name = rec.name.title() if rec.name else ''

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
    birth_date = fields.Date('Birth Date')
    age = fields.Integer('Age')
    phone = fields.Char('Phone')
    email = fields.Char('Email Contact')
    role = fields.Char('Role')
    note = fields.Html('Notes')
    country_id = fields.Many2one('res.country', 'Nationality')
    active = fields.Boolean('Active?', default=True)

    @api.onchange('birth_date')
    def _onchange_birth_date(self):
        """Method to set upper for name"""
        curr_date = fields.Date.today()
        for rec in self:
            birth_date = rec.birth_date
            rec.age = curr_date.year - birth_date.year -\
                      ((curr_date.month, curr_date.day) < (birth_date.month, birth_date.day))\
                if birth_date else ''

    @api.onchange('name')
    def _onchange_name_upper(self):
        """Method to set upper for name"""
        for rec in self:
            rec.name = rec.name.title() if rec.name else ''








