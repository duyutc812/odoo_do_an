from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning
from datetime import datetime, date
from dateutil.relativedelta import relativedelta as rd
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import pytz


class Card(models.Model):
    _name = 'library.card'
    _description = "Library Card Information"
    _rec_name = 'code'

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s - %s' % (rec.code, rec.gt_name)))
        return res

    book_limit = fields.Integer('No of Book on Card', required=True, default=1)
    user = fields.Selection([('student', 'Student'), ('teacher', 'Teacher')], string='User')
    student_id = fields.Many2one('library.student', string='Student Name')
    teacher_id = fields.Many2one('library.teacher', string='Teacher Name')
    gt_name = fields.Char(compute="_compute_name", method=True, string='Name')

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

    stage_id = fields.Many2one('library.card.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               )
    state = fields.Selection(related='stage_id.state', store=True)

    start_date = fields.Date('Start Date', default=fields.Date.today())
    duration = fields.Integer('Duration', help="Duration in months", default=1)
    end_date = fields.Date('End Date', compute="_compute_end_date", store=True)
    active = fields.Boolean('Active', default=True)

    code = fields.Char(string='Code', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    borrowed_book = fields.Integer(string="Borrowed Book",
                                   compute='_compute_check_borrowed_book',
                                   readonly=True)

    """get name for user : student or teacher"""
    @api.depends('student_id')
    def _compute_name(self):
        for rec in self:
            if rec.student_id:
                user = rec.student_id.name
            else:
                user = rec.teacher_id.name
            rec.gt_name = user

    """get end_date for card"""
    @api.depends('start_date', 'duration')
    def _compute_end_date(self):
        for rec in self:
            if rec.start_date:
                rec.end_date = rec.start_date + rd(months=rec.duration)

    @api.multi
    def library_card_expire(self):
        """method get card expire and confirm"""
        current_date = datetime.now()
        print('excute scheduled action')
        # print(current_date)
        # print(type(self.env.user.tz))
        # if self.env.user.tz != True:
        #     print('abc')
        #     raise ValidationError('miss timezone', 'kjsakfjk')
        user_tz = pytz.timezone(self.env.context.get('tz') or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        # print(date_today)
        lib_card_search = self.search([('state', '=', 'running'),
                                                           ('end_date', '<', date_today)])
        lib_card_expire_error = self.search([('state', '=', 'expire'),
                                                                 ('end_date', '>', date_today)])
        # print(lib_card_search)
        # print(lib_card_expire_error)
        Stages = self.env['library.card.stage']
        if lib_card_expire_error:
            for lib_card_running in lib_card_expire_error:
                lib_card_running.stage_id = Stages.search([('state', '=', 'running')])

        if lib_card_search:
            for lib_card_expire in lib_card_search:
                lib_card_expire.stage_id = Stages.search([('state', '=', 'expire')])

    @api.constrains('student_id', 'teacher_id')
    def _constrains_check_member_card(self):
        if self.user == 'student':
            # print(self.ids)
            """ids la id cua record sap tao"""
            student_lib_card = self.search([
                ('student_id', '=', self.student_id.id),
                ('state', '!=', 'expire'),
                ('id', 'not in', self.ids)
            ])
            # print(student_lib_card)
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
        print(self.stage_id)
        self.start_date = fields.Date.today()
        return {
            # effect when confirm Library card record
            'effect': {
                'fadeout': 'slow',
                'message': 'Library Card ' + str(self.code) + ' confirmed .... Thank You',
                'type': 'rainbow_man',
            }
        }

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

    @api.multi
    def draft_state(self):
        self.stage_id = self.env['library.card.stage'].search([('state', '=', 'draft')])

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state == 'running' or rec.state == 'expire':
                raise ValidationError('You cannot delete a confirmed or expire library card!')
            elif rec.state == 'draft':
                # print('abc la abc bâc')
                checkout_card = self.env['library.checkout'].search_count([
                    ('card_id', '=', rec.id)
                ])
                if checkout_card:
                    raise ValidationError('Can not delete! related record')
        return super(Card, self).unlink()

    @api.constrains('book_limit', 'duration')
    def _constrains_book_limit(self):
        if self.book_limit <= 0 or self.duration < 0:
            raise ValidationError('No of Book on Card and Duration must be great 0')

    def _compute_check_borrowed_book(self):
        borrowed_book = self.env['library.checkout'].search_count([
            ('card_id', '=', self.id),
            ('state', '=', 'running'),
        ])
        # print(borrowed_book)
        self.borrowed_book = borrowed_book








