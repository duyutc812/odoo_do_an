from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning, UserError
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
                                related='duration_id.book_on_card', store=True)
    limit_syllabus = fields.Integer('No of Syllabus on Card', readonly=True,
                                    related='duration_id.syllabus_on_card', store=True)

    currency_id = fields.Many2one('res.currency', 'Currency', related='duration_id.currency_id', store=True)
    price = fields.Monetary('Price', 'currency_id', compute='_compute_price', store=True)
    user = fields.Selection([('student', 'Student'), ('teacher', 'Teacher')], string='User', track_visibility='always')
    student_id = fields.Many2one('library.student', string='Student Name', track_visibility='always')
    teacher_id = fields.Many2one('library.teacher', string='Teacher Name', track_visibility='always')
    gt_name = fields.Char(compute="_compute_gt_name", method=True, string='Name')
    email = fields.Char('Email User', compute='_compute_email', method=True, store=True)
    stage_id = fields.Many2one('library.card.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               track_visibility='always')
    state = fields.Selection(related='stage_id.state', store=True)
    start_date = fields.Date('Start Date', default=fields.Date.today(), track_visibility='always')
    duration_id = fields.Many2one('library.duration', string='Duration', track_visibility='always')
    end_date = fields.Date('End Date', compute="_compute_end_date", store=True, track_visibility='always')
    user_id = fields.Many2one('res.users', 'Librarian',
                              default=lambda s: s.env.uid,
                              readonly=True)

    active = fields.Boolean('Active', default=True)

    code = fields.Char(string='Code', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    chk_mg_new = fields.Integer(string="Borrowed Book",
                                compute='_compute_chk_mg_new',
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
    count = fields.Integer(compute='_compute_count')

    # kanban_state = fields.Selection(
    #     [('grey', 'Draft'),
    #      ('red', 'Penalty'),
    #      ('green', 'Confirm')],
    #     string='Kanban State', compute='_compute_kanban_state')

    @api.onchange('is_penalty')
    def _onchange_is_penalty(self):
        if not self.is_penalty:
            self.duration_penalty = ''
            self.end_date_penalty = ''
            self.note = ''

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
            lib_card.message_post(_('Penalty Card'))
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'library.card',
                'res_id': lib_card.id,
                'context': context
            }

    def cancel_penalty_card(self):
        for lib_card in self:
            lib_card.is_penalty = False
            lib_card._onchange_is_penalty()
            lib_card.message_post(_('Canceled Penalty Card'))

    @api.multi
    def running_state(self):
        stage_running = self.env['library.card.stage'].search([('state', '=', 'running')])
        for lib_card in self:
            lib_card.code = self.env['ir.sequence'].next_by_code('library.card.sequence') or _('New')
            lib_card.stage_id = stage_running
            # print(self.stage_id)
            lib_card.start_date = fields.Date.today()
            return {
                # effect when confirm Library card record
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Library Card ' + str(lib_card.code) + ' confirmed .... Thank You',
                    'type': 'rainbow_man',
                }
            }

    @api.multi
    def draft_state(self):
        stage_draft = self.env['library.card.stage'].search([('state', '=', 'draft')])
        for lib_card in self:
            lib_card.stage_id = stage_draft
            lib_card.price = 0
            lib_card.is_penalty = False
            lib_card._onchange_is_penalty()
            lib_card.code = 'New'

    @api.depends('student_id', 'teacher_id')
    def _compute_email(self):
        for lib_card in self:
            lib_card.email = lib_card.student_id.email if lib_card.student_id else lib_card.teacher_id.email

    @api.onchange('user')
    def _onchange_user(self):
        if self.user == 'student':
            self.teacher_id = ''
        elif self.user == 'teacher':
            self.student_id = ''
        self.email = ''
        self.duration_id = ''
        return {'domain': {'duration_id': [('user_type', '=', self.user)]}}

    @api.multi
    def name_get(self):
        res = []
        for lib_card in self:
            res.append((lib_card.id, '%s - %s' % (lib_card.code, lib_card.gt_name)))
        return res

    @api.depends('duration_id', 'stage_id')
    def _compute_price(self):
        stage_draft = self.env['library.card.stage'].search([('state', '=', 'draft')])
        for lib_card in self:
            if lib_card.duration_id and lib_card.stage_id != stage_draft:
                lib_card.price = lib_card.duration_id.price

    """get name for user : student or teacher"""
    @api.depends('student_id')
    def _compute_gt_name(self):
        for lib_card in self:
            lib_card.gt_name = lib_card.student_id.name if lib_card.student_id else lib_card.teacher_id.name

    """get end_date for card"""
    @api.depends('start_date', 'duration_id')
    def _compute_end_date(self):
        for lib_card in self:
            if lib_card.start_date:
                lib_card.end_date = lib_card.start_date + rd(months=int(lib_card.duration_id.duration))

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
                raise ValidationError(_('You cannot assign library card to same student more than once!'))
        if self.user == 'teacher':
            # print(self.ids)
            teacher_lib_card = self.search([
                ('teacher_id', '=', self.teacher_id.id),
                ('state', '!=', 'expire'),
                ('id', '!=', self.id)
            ])
            # print(teacher_lib_card)
            if teacher_lib_card:
                raise ValidationError(_('You cannot assign library card to same teacher more than once!'))

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state == 'running' or rec.state == 'expire':
                raise ValidationError(_('You cannot delete a confirmed or expire library card!'))
            # elif rec.state == 'draft':
            #     checkout_card = self.env['library.checkout'].search_count([
            #         ('card_id', '=', rec.id)
            #     ])
            #     if checkout_card:
            #         raise ValidationError('Can not delete! related record')elif rec.state == 'draft':
            #     checkout_card = self.env['library.checkout'].search_count([
            #         ('card_id', '=', rec.id)
            #     ])
            #     if checkout_card:
            #         raise ValidationError('Can not delete! related record')
        return super(Card, self).unlink()

    def _compute_count(self):
        chk_at_lib = self.env['library.checkout.at.lib'].search_count([
            ('card_id', '=', self.id),
        ])
        self.count = chk_at_lib

    @api.multi
    def library_check_card_expire(self):
        """method get card expire and confirm"""
        current_date = datetime.now()
        print('scheduled action check card expire and cancel penalty card')
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        print(date_today)
        Stages = self.env['library.card.stage']
        lib_card_cancel_penalty = self.search([('is_penalty', '=', True),
                                               ('code', '!=', 'New'),
                                               ('state', '=', 'running'),
                                               ('end_date_penalty', '<', date_today)])
        if lib_card_cancel_penalty:
            for lib_card in lib_card_cancel_penalty:
                lib_card.is_penalty = False
                lib_card._onchange_is_penalty()
                lib_card.message_post(_('Scheduled Action: Canceled Penalty'))
        lib_card_expire = self.search([('end_date', '<', date_today),
                                       ('code', '!=', 'New')])
        if lib_card_expire:
            for lib_card in lib_card_expire:
                lib_card.stage_id = Stages.search([('state', '=', 'expire')])

        # lib_card_running = self.search([('end_date', '>', date_today),
        #                                 ('code', '!=', 'New')])
        # lib_card_draft = self.search([('code', '=', 'New')])
        # print('Running : ', lib_card_running)
        # print('Expire: ', lib_card_expire)
        # if lib_card_running:
        #     for lib_card in lib_card_running:
        #         lib_card.stage_id = Stages.search([('state', '=', 'running')])
        #
        # if lib_card_draft:
        #     for lib_card in lib_card_draft:
        #         lib_card.stage_id = Stages.search([('state', '=', 'draft')])

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

    def send_email(self):
        template_id = self.env.ref('do_an_tn.library_card_email_template').id
        template = self.env['mail.template'].browse(template_id)
        # trả về id của thằng template
        for lib_card in self:
            if not lib_card.email:
                raise UserError(_("Cannot send email: user %s has no email address.") % lib_card.gt_name)
            # print('template: ', template, '\n', 'template_id: ', template_id)
            # self.env['email.template'].browse(template_id).send_mail(self.id, force_send=True)
            template.send_mail(lib_card.id, force_send=True, raise_exception=True)
            print('Send Email to user ID: ', lib_card.id)
            return self.message_post(_('Send Email for Card'))









