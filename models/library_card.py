from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning, UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta as rd
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import pytz


class Card(models.Model):
    _name = 'lib.card'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Thẻ thư viện"
    _rec_name = 'name_seq'

    @api.model
    def _default_stage(self):
        return self.env['lib.card.stage'].search([], limit=1)

    @api.model
    def _group_expand_stage_id(self, stages, domain, order):
        # print(stages)
        # print(order)
        # lib.card.stage()
        # sequence, name
        return stages.search([], order=order)

    @api.multi
    def print_report(self):
        return self.env.ref('do_an_tn.action_library_card_detail').report_action(self)

    name_seq = fields.Char(string='Mã thẻ mượn', required=True, copy=False, readonly=True, index=True,
                           default=lambda self: _('New'))
    member_type = fields.Selection([
        ('student', 'Sinh viên'),
        ('teacher', 'Giảng viên')],
        string='Độc giả', track_visibility='always')
    student_id = fields.Many2one('lib.student', string='Mã sinh viên', track_visibility='always')
    teacher_id = fields.Many2one('lib.teacher', string='Mã giảng viên', track_visibility='always')
    gt_name = fields.Char(compute="_compute_gt_name", method=True, string='Tên độc giả')
    email = fields.Char('Email độc giả', compute='_compute_email', method=True, store=True)
    student_image = fields.Binary(related='student_id.student_image', store=True, string="Ảnh sinh viên")
    teacher_image = fields.Binary(related='teacher_id.teacher_image', store=True, string="Ảnh giảng viên")
    book_limit = fields.Integer('Tài liệu tham khảo', readonly=True,
                                related='duration_id.book_limit', store=True)
    syllabus_limit = fields.Integer('Giáo trình', readonly=True,
                                    related='duration_id.syllabus_limit', store=True)
    stage_id = fields.Many2one('lib.card.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               track_visibility='always')
    state = fields.Selection(related='stage_id.state', store=True)
    start_date = fields.Date('Ngày bắt đầu', default=fields.Date.today(), track_visibility='always')
    duration_id = fields.Many2one('lib.duration', string='Thời hạn', track_visibility='always')
    end_date = fields.Date('Ngày hết hạn', compute="_compute_end_date", store=True, track_visibility='always')

    currency_id = fields.Many2one('res.currency', 'Tiền tệ', related='duration_id.currency_id', store=True)
    price = fields.Monetary('Giá tiền', 'currency_id', compute='_compute_price', store=True)
    user_id = fields.Many2one('res.users', 'Nhân viên thư viện',
                              default=lambda s: s.env.uid,
                              readonly=True, required=True,
                              )
    is_penalty = fields.Boolean('Bị Phạt?', default=False)
    duration_penalty = fields.Selection([
        ('2_week', '2 tuần'),
        ('1_month', '1 tháng'),
    ], string='Thời hạn phạt')
    end_date_penalty = fields.Date('Ngày kết thúc phạt',
                                   compute='_compute_end_date_penalty', store=True)
    note = fields.Char('Ghi chú')
    is_active = fields.Boolean('Có hiệu lực?', default=True)
    count_al = fields.Integer(compute='_compute_count')
    count_bh = fields.Integer(compute='_compute_count')

    # kanban_state = fields.Selection(
    #     [('grey', 'Draft'),
    #      ('red', 'Penalty'),
    #      ('green', 'Confirm')],
    #     string='Kanban State', compute='_compute_kanban_state')

    @api.constrains('member_type', 'duration_id')
    def _constraint_member_type_duration_id(self):
        if self.member_type != self.duration_id.member_type:
            raise ValidationError(_('Hãy chọn lại thời hạn của thẻ thư viện!'))

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
            lib_card.message_post(_('Thẻ mượn đã bị phạt'))
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'lib.card',
                'res_id': lib_card.id,
                'context': context
            }

    def cancel_penalty_card(self):
        for lib_card in self:
            lib_card.is_penalty = False
            lib_card._onchange_is_penalty()
            lib_card.message_post(_('Đã huỷ phạt thẻ mượn'))

    @api.multi
    def running_state(self):
        stage_running = self.env['lib.card.stage'].search([('state', '=', 'running')])
        for lib_card in self:
            lib_card.name_seq = self.env['ir.sequence'].next_by_code('lib.card.sequence') or _('New')
            lib_card.stage_id = stage_running
            # print(self.stage_id)
            lib_card.start_date = fields.Date.today()
            return {
                # effect when confirm Library card record
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Thẻ thư viện ' + str(lib_card.name_seq) + ' đã được tạo thành công!',
                    'type': 'rainbow_man',
                }
            }

    @api.multi
    def draft_state(self):
        stage_draft = self.env['lib.card.stage'].search([('state', '=', 'draft')])
        stage_running = self.env['lib.card.stage'].search([('state', '=', 'running')])
        chk_at_lib = self.env['lib.checkout.at.lib'].search([('state', '=', 'running')])
        chk_back_home = self.env['lib.checkout.back.home'].search([('state', '=', 'running')])
        for lib_card in self:
            if lib_card.stage_id == stage_running:
                if chk_at_lib.filtered(lambda s: s.card_id.id == lib_card.id) or \
                        chk_back_home.filtered(lambda s: s.card_id.id == lib_card.id):
                    raise ValidationError(_('Không thể chuyển trạng thái \'Nháp\' khi có phiếu mượn đang hoạt động!'))
            lib_card.stage_id = stage_draft
            lib_card.price = 0
            lib_card.is_penalty = False
            lib_card._onchange_is_penalty()
            lib_card.name_seq = _('New')

    @api.depends('student_id', 'teacher_id')
    def _compute_email(self):
        for lib_card in self:
            lib_card.email = lib_card.student_id.email if lib_card.student_id else lib_card.teacher_id.email

    @api.onchange('member_type')
    def _onchange_member_type(self):
        if self.member_type == 'student':
            self.teacher_id = ''
        elif self.member_type == 'teacher':
            self.student_id = ''
        self.email = ''
        self.duration_id = ''
        return {'domain': {'duration_id': [('member_type', '=', self.member_type)]}}

    @api.multi
    def name_get(self):
        res = []
        for lib_card in self:
            res.append((lib_card.id, '%s - %s' % (lib_card.name_seq, lib_card.gt_name)))
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|', '|', '|', ('email', operator, name), ('name_seq', operator, name), ('student_id.name', operator, name), ('teacher_id.name', operator, name)]
        return super(Card, self).search(domain, limit=limit).name_get()

    @api.depends('duration_id', 'stage_id')
    def _compute_price(self):
        stage_draft = self.env['lib.card.stage'].search([('state', '=', 'draft')])
        for lib_card in self:
            if lib_card.duration_id and lib_card.stage_id != stage_draft:
                lib_card.price = lib_card.duration_id.price

    @api.depends('student_id')
    def _compute_gt_name(self):
        for lib_card in self:
            lib_card.gt_name = lib_card.student_id.name if lib_card.student_id else lib_card.teacher_id.name

    @api.depends('start_date', 'duration_id')
    def _compute_end_date(self):
        for lib_card in self:
            if lib_card.start_date:
                lib_card.end_date = lib_card.start_date + rd(months=int(lib_card.duration_id.duration))

    @api.constrains('student_id', 'teacher_id')
    def _constrains_check_member_card(self):
        if self.member_type == 'student':
            # print(self.ids)
            """ids la id cua record sap tao"""
            student_lib_card = self.sudo().search([
                ('student_id', '=', self.student_id.id),
                ('state', '!=', 'expire'),
                ('id', 'not in', self.ids)
            ])
            # print(student_lib_card)
            if student_lib_card:
                raise ValidationError(_('Không thể tạo nhiều thẻ với cùng một sinh viên!'))
        if self.member_type == 'teacher':
            # print(self.ids)
            teacher_lib_card = self.sudo().search([
                ('teacher_id', '=', self.teacher_id.id),
                ('state', '!=', 'expire'),
                ('id', '!=', self.id)
            ])
            # print(teacher_lib_card)
            if teacher_lib_card:
                raise ValidationError(_('Không thể tạo nhiều thẻ với cùng một giảng viên!'))

    def _compute_count(self):
        chk_at_lib = self.env['lib.checkout.at.lib'].sudo().search_count([
            ('card_id', '=', self.id),
        ])
        chk_back_home = self.env['lib.checkout.back.home'].sudo().search_count([
            ('card_id', '=', self.id),
        ])
        self.count_al = chk_at_lib
        self.count_bh = chk_back_home

    @api.multi
    def library_check_card_expire(self):
        """method get card expire and confirm"""
        current_date = datetime.now()
        print('Hoạt động theo lịch trình: kiểm tra thẻ hết hạn và thẻ bị phạt')
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        print(date_today)
        Stages = self.env['lib.card.stage']
        lib_card_cancel_penalty = self.sudo().search([('is_penalty', '=', True),
                                               ('name_seq', '!=', _('New')),
                                               ('state', '=', 'running'),
                                               ('end_date_penalty', '<', date_today)])
        if lib_card_cancel_penalty:
            for lib_card in lib_card_cancel_penalty:
                lib_card.is_penalty = False
                lib_card._onchange_is_penalty()
                lib_card.message_post(_('Hoạt động lịch trình: Huỷ phạt thẻ'))
        lib_card_expire = self.sudo().search([('end_date', '<', date_today),
                                       ('name_seq', '!=', _('New'))])
        if lib_card_expire:
            for lib_card in lib_card_expire:
                lib_card.stage_id = Stages.sudo().search([('state', '=', 'expire')])

        lib_card_running = self.search([('end_date', '>', date_today),
                                        ('state', '!=', 'draft')])

        if lib_card_running:
            for lib_card in lib_card_running:
                lib_card.stage_id = Stages.search([('state', '=', 'running')])

    @api.multi
    def library_card_send_email(self):
        current_date = datetime.now()
        print('Hoạt động lịch trình: gửi email thông báo thẻ mượn hết hạn vào sau 1 tuần nữa')
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        lib_card_will_expire = self.sudo().search([('end_date', '=', (date_today + rd(days=7))),
                                                   ('name_seq', '!=', _('New'))])
        print((date_today + rd(days=7)).date())
        print(lib_card_will_expire)
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
            lib_card.email = lib_card.student_id.email if lib_card.student_id else lib_card.teacher_id.email
            if not lib_card.email:
                raise UserError(_("Không thể gửi email: độc giả %s không có địa chỉ email.") % lib_card.gt_name)
            # print('template: ', template, '\n', 'template_id: ', template_id)
            # self.env['email.template'].browse(template_id).send_mail(self.id, force_send=True)
            template.send_mail(lib_card.id, force_send=True, raise_exception=True)
            print('Gửi email tới người dùng có ID: ', lib_card.id)
            return self.message_post(_('Đã gửi email cho độc giả của thẻ này!'))

    @api.multi
    def unlink(self):
        for card in self:
            if card.state == 'running':
                # or rec.state == 'expire'
                raise ValidationError(_('Không thể xoá thẻ thư viện ở trạng thái đang hoạt động!'))
            else:
                checkout_al = self.env['lib.checkout.at.lib'].search([('card_id', '=', card.id)], limit=1)
                checkout_bh = self.env['lib.checkout.back.home'].search([('card_id', '=', card.id)], limit=1)
                if checkout_al or checkout_bh:
                    raise ValidationError('Không thể xóa thẻ mượn do có phiếu mượn liên quan đến thẻ nữa!')
        return super(Card, self).unlink()









