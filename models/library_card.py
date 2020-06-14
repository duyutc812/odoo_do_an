from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning
from datetime import datetime, date
from dateutil.relativedelta import relativedelta as rd
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import pytz


class Card(models.Model):
    _name = 'library.card'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Library Card Information"
    _rec_name = 'code'

    @api.model
    def _default_stage(self):
        return self.env['library.card.stage'].search([], limit=1)

    @api.model
    def _group_expand_stage_id(self, stages, domain, order):
        # print(stages)
        # print(order)
        # library.card.stage()
        # sequence, name
        return stages.search([], order=order)

    @api.multi
    def print_report(self):
        return self.env.ref('do_an_tn.action_library_card_detail').report_action(self)

    book_limit = fields.Integer('No of Book on Card', readonly=True,
                                compute='_compute_book_limit', store=True)
    book_limit_syllabus = fields.Integer('No of Syllabus on Card', readonly=True,
                                         compute='_compute_book_limit', store=True)
    price = fields.Integer('Price', compute='_compute_book_limit', store=True)
    user = fields.Selection([('student', 'Student'), ('teacher', 'Teacher')], string='User', track_visibility='always')
    student_id = fields.Many2one('library.student', string='Student Name', track_visibility='always')
    teacher_id = fields.Many2one('library.teacher', string='Teacher Name', track_visibility='always')
    gt_name = fields.Char(compute="_compute_gt_name", method=True, string='Name')
    email = fields.Char('Email User', compute='_compute_email', method=True, store=True)
    # user_id = fields.Many2one('res.users', default=lambda s: s.env.uid)
    stage_id = fields.Many2one('library.card.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               track_visibility='always')
    state = fields.Selection(related='stage_id.state', store=True)

    start_date = fields.Date('Start Date', default=fields.Date.today(), track_visibility='always')
    duration = fields.Selection([
        ('3', '3 months'),
        ('6', '6 months'),
    ], string='Duration', default='3', track_visibility='always')
    end_date = fields.Date('End Date', compute="_compute_end_date", store=True, track_visibility='always')
    active = fields.Boolean('Active', default=True)

    code = fields.Char(string='Code', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    chk_card = fields.Integer(string="Borrowed Book",
                              compute='_compute_chk_card',
                              readonly=True)
    color = fields.Integer('Color')

    is_penalty = fields.Boolean('Penalty', default=False)
    duration_penalty = fields.Selection([
        ('2_week', '2 weeks'),
        ('1_month', '1 month'),
    ], string='Duration Penalty')
    end_date_penalty = fields.Date('End Date Penalty',
                                   compute='_compute_end_date_penalty', store=True)
    note = fields.Char('Note')

    @api.depends('duration_penalty')
    def _compute_end_date_penalty(self):
        current_date = datetime.now()
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        for lib_card in self:
            if lib_card.is_penalty:
                if lib_card.duration_penalty == '2_week':
                    lib_card.end_date_penalty = date_today.date() + rd(days=14)
                else:
                    lib_card.end_date_penalty = date_today.date() + rd(months=1)
            if lib_card.end_date_penalty and lib_card.end_date_penalty > lib_card.end_date:
                lib_card.end_date_penalty = lib_card.end_date

    def penalty_card(self):
        for lib_card in self:
            lib_card.duration_penalty = ''
            lib_card.end_date_penalty = ''
            lib_card.note = ''
            lib_card.is_penalty = True
            # message = 'Penalty Card from %s' % \
            #           (str(date_today.date()) + '%s' % ('to ' + str(lib_card.end_date_penalty) if lib_card.end_date_penalty else '')
            #            + str(lib_card.note))
            lib_card.message_post(body='Penalty Card')

    def cancel_penalty_card(self):
        for lib_card in self:
            lib_card.is_penalty = False
            lib_card.duration_penalty = ''
            lib_card.end_date_penalty = ''
            lib_card.note = ''
            lib_card.message_post(body='Canceled Penalty Card')
            
    @api.depends('student_id', 'teacher_id')
    def _compute_email(self):
        for lib_card in self:
            if lib_card.student_id:
                lib_card.email = lib_card.student_id.email
            elif lib_card.teacher_id:
                lib_card.email = lib_card.teacher_id.email

    @api.onchange('user')
    def _onchange_user(self):
        for lib_card in self:
            if lib_card.user == 'student':
                lib_card.teacher_id = ''
                lib_card.email = ''
            elif lib_card.user == 'teacher':
                lib_card.student_id = ''
                lib_card.email = ''

    @api.multi
    def name_get(self):
        res = []
        for lib_card in self:
            res.append((lib_card.id, '%s - %s' % (lib_card.code, lib_card.gt_name)))
        return res

    @api.depends('user', 'duration', 'state')
    def _compute_book_limit(self):
        for lib_card in self:
            if lib_card.user == 'student':
                if lib_card.duration == '3':
                    lib_card.book_limit = 1
                    lib_card.book_limit_syllabus = 1
                    lib_card.price = 20000 if lib_card.state != 'draft' else 0
                else:
                    lib_card.book_limit = 2
                    lib_card.price = 30000 if lib_card.state != 'draft' else 0
                lib_card.book_limit_syllabus = 1
            elif lib_card.user == 'teacher':
                lib_card.duration = '6'
                lib_card.book_limit = 3
                lib_card.book_limit_syllabus = 2
                lib_card.price = 0

    """get name for user : student or teacher"""
    @api.depends('student_id')
    def _compute_gt_name(self):
        for lib_card in self:
            lib_card.gt_name = lib_card.student_id.name if lib_card.student_id else lib_card.teacher_id.name

    """get end_date for card"""
    @api.depends('start_date', 'duration')
    def _compute_end_date(self):
        for lib_card in self:
            if lib_card.start_date:
                lib_card.end_date = lib_card.start_date + rd(months=int(lib_card.duration))

    @api.multi
    def library_check_card_expire(self):
        """method get card expire and confirm"""
        current_date = datetime.now()
        print('scheduled action')
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        print(date_today)
        lib_card_expire = self.search([('end_date', '<', date_today),
                                       ('code', '!=', 'New')])
        lib_card_running = self.search([('end_date', '>', date_today),
                                        ('code', '!=', 'New')])
        lib_card_draft = self.search([('code', '=', 'New')])
        # print('Running : ', lib_card_running)
        # print('Expire: ', lib_card_expire)
        Stages = self.env['library.card.stage']
        if lib_card_running:
            for lib_card in lib_card_running:
                lib_card.stage_id = Stages.search([('state', '=', 'running')])

        if lib_card_expire:
            for lib_card in lib_card_expire:
                lib_card.stage_id = Stages.search([('state', '=', 'expire')])

        if lib_card_draft:
            for lib_card in lib_card_draft:
                lib_card.stage_id = Stages.search([('state', '=', 'draft')])

    @api.multi
    def library_card_send_email(self):
        current_date = datetime.now()
        print('scheduled of send email')
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        print(user_tz)
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        print(date_today)
        lib_card_will_expire = self.search([('end_date', '=', date_today),
                                            ('code', '!=', 'New')])
        print(lib_card_will_expire)
        print('abc')
        for lib_card in lib_card_will_expire:
            template_id = self.env.ref('do_an_tn.lib_card_send_email_expire').id
            template = self.env['mail.template'].browse(template_id)
            # print('template: ', template, '\n', 'template_id: ', template_id)
            # self.env['email.template'].browse(template_id).send_mail(self.id, force_send=True)
            template.send_mail(lib_card.id, force_send=True)
            print(lib_card.id)

    @api.constrains('student_id', 'teacher_id')
    def _constrains_check_member_card(self):
        if self.user == 'student':
            print(self.ids)
            """ids la id cua record sap tao"""
            student_lib_card = self.search([
                ('student_id', '=', self.student_id.id),
                ('state', '!=', 'expire'),
                ('id', 'not in', self.ids)
            ])
            print(student_lib_card)
            if student_lib_card:
                raise ValidationError('You cannot assign library card to same student more than once!')
        if self.user == 'teacher':
            # print(self.ids)
            teacher_lib_card = self.search([
                ('teacher_id', '=', self.teacher_id.id),
                ('state', '!=', 'expire'),
                ('id', '!=', self.id)
            ])
            # print(teacher_lib_card)
            if teacher_lib_card:
                raise ValidationError('You cannot assign library card to same teacher more than once!')

    @api.multi
    def running_state(self):
        if self.code == 'New':
            self.code = self.env['ir.sequence'].next_by_code('library.card.sequence') or _('New')
        Stages = self.env['library.card.stage']
        self.stage_id = Stages.search([('state', '=', 'running')])
        # print(self.stage_id)
        self.start_date = fields.Date.today()
        return {
            # effect when confirm Library card record
            'effect': {
                'fadeout': 'slow',
                'message': 'Library Card ' + str(self.code) + ' confirmed .... Thank You',
                'type': 'rainbow_man',
            }
        }

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state == 'running' or rec.state == 'expire':
                raise ValidationError('You cannot delete a confirmed or expire library card!')
            elif rec.state == 'draft':
                checkout_card = self.env['library.checkout'].search_count([
                    ('card_id', '=', rec.id)
                ])
                if checkout_card:
                    raise ValidationError('Can not delete! related record')
        return super(Card, self).unlink()

    def _compute_chk_card(self):
        chk_card = self.env['library.checkout'].search_count([
            ('card_id', '=', self.id),
            ('state', '=', 'running'),
        ])
        self.chk_card = chk_card

    def send_email(self):
        # trả về id của thằng template
        template_id = self.env.ref('do_an_tn.library_card_email_template').id
        template = self.env['mail.template'].browse(template_id)
        # print('template: ', template, '\n', 'template_id: ', template_id)
        # self.env['email.template'].browse(template_id).send_mail(self.id, force_send=True)
        template.send_mail(self.id, force_send=True)
        print('Send Email to user ID: ', self.id)
        return self.message_post(body='Send Email for Card Expire', subject='Send Email')

    # @api.multi
    # def expire_state(self):
    #     self.stage_id = self.env['library.card.stage'].search([('state', '=', 'expire')])

    # """upgrade field code and constrain when drag kanban from draft to confirm"""
    # @api.multi
    # def write(self, vals):
    #     """vals: nhung thay doi kieu dictionary : {'duration': 2}"""
    #     # print(self)
    #     # library.card(69, )
    #     # print(vals)
    #     # {'duration': 2}
    #
    #     if self.state == 'draft' and vals['state'] == 'expire':
    #         # print('abc')
    #         raise ValidationError('You can not change state kanban from draft to expire!')
    #     elif self.state == 'expire' and vals['state'] == 'draft':
    #         raise ValidationError('You can not change state kanban from expire to draft!')
    #     return super(Card, self).write(vals)
    #     # print(self.state)
    #     # print(vals['state'])

    # @api.multi
    # def draft_state(self):
    #     self.stage_id = self.env['library.card.stage'].search([('state', '=', 'draft')])










