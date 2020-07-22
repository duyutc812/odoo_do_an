from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta as rd
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import pytz
from collections import Counter


class CheckoutBackHome(models.Model):
    _name = 'lib.checkout.back.home'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Phiếu mượn về nhà'

    @api.model
    def _default_stage(self):
        return self.env['lib.checkout.stage'].search([], limit=1)

    @api.model
    def _group_expand_stage_id(self, stages, domain, order):
        return stages.search([], order=order)

    name_seq = fields.Char(string="Mã phiếu mượn", default=lambda self: _('New'), readonly=True)
    card_id = fields.Many2one('lib.card', string="Mã thẻ mượn",
                              required=True,
                              domain=[('state', '=', 'running'), ('is_penalty', '=', False)])
    state_card = fields.Selection(related='card_id.state', store=True, string='Trạng thái thẻ mượn')
    stage_id = fields.Many2one('lib.checkout.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               )
    state = fields.Selection(related='stage_id.state', store=True, string='Trạng thái phiếu mượn')
    gt_name = fields.Char(related='card_id.gt_name', string='Tên độc giả', store=True)
    end_date = fields.Date(related='card_id.end_date', string='Ngày hết hạn', store=True)
    type_document = fields.Selection([
        ('book', 'Sách'),
        ('project', 'Đồ án - luận văn'),
    ], string='Loại tài liệu', required=True)

    book_id = fields.Many2one('lib.book', 'Tiêu đề')
    meta_book_id = fields.Many2one('lib.meta.books', string='Meta sách')
    project_id = fields.Many2one('lib.document.project', 'Đồ án - luận văn')
    meta_project_id = fields.Many2one('lib.meta.projects', string='Meta đồ án - luận văn')
    status_document = fields.Text('Tình trạng', compute='_compute_status_document_doc_price', store=True)
    category_doc = fields.Many2one(string='Thể loại', related='book_id.category', store=True)
    doc_price = fields.Monetary("Giá tiền", 'currency_id', compute='_compute_status_document_doc_price', store=True)
    currency_id = fields.Many2one('res.currency', 'Tiền tệ',
                                  default=lambda s: s.env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1))
    penalty_chk_price = fields.Monetary('Tiền phạt phiếu mượn', 'currency_id')
    penalty_doc_price = fields.Monetary('Tiền phạt tài liệu', 'currency_id')
    penalty_total = fields.Monetary('Tổng tiền phạt', 'currency_id', compute="_compute_penalty_total", store=True)
    day_overdue = fields.Integer('Ngày quá hạn')
    note = fields.Char('Ghi chú')
    document_term = fields.Integer('Giới hạn mượn(ngày)', compute='_compute_status_document_doc_price', store=True)

    user_id = fields.Many2one('res.users', 'Nhân viên thư viện',
                              default=lambda s: s.env.uid,
                              readonly=True, required=True)
    user_image = fields.Binary(related='user_id.image', store=True)
    borrow_date = fields.Datetime(string="Ngày mượn", readonly=True)
    return_date = fields.Date(string="Ngày hẹn trả")
    actual_return_date = fields.Datetime(string="Ngày trả thực tế")
    priority = fields.Selection(
        [('0', 'Thấp'),
         ('1', 'Bình thường'),
         ('2', 'Cao')],
        'Ưu tiên',
        default='0')
    kanban_state = fields.Selection(
        [('normal', 'Bình thường'),
         ('overdue', 'Quá hạn mượn')],
        'Trạng thái Kanban',
        default='normal')
    email = fields.Char('Email', related='card_id.email', store=True)
    count_doc = fields.Integer(string="Tài liệu", compute='_compute_count_chk_bh')
    count_syl = fields.Integer(string="Giáo trình", compute='_compute_count_chk_bh')
    count_penalty = fields.Integer(string="Phạt", compute='_compute_count_chk_bh')
    count_waiting = fields.Integer(string="Đang chờ", compute='_compute_count_chk_bh')

    @api.multi
    def name_get(self):
        res = []
        for chk in self:
            res.append((chk.id, '%s - %s' % (chk.name_seq, chk.gt_name)))
        return res

    @api.onchange('card_id')
    def onchange_card_id(self):
        syll_cate = self.env.ref('do_an_tn.data_category_6').id
        chk_running_syl = self.sudo().search([('card_id', '=', self.card_id.id),
                                              ('state', '=', 'running'),
                                              ('id', 'not in', self.ids),
                                              ('category_doc', '=', syll_cate)])
        chk_running_bk = self.sudo().search([('card_id', '=', self.card_id.id),
                                             ('state', '=', 'running'),
                                             ('id', 'not in', self.ids),
                                             ('category_doc', '!=', syll_cate)])
        if self.card_id :
            if len(chk_running_syl) >= self.card_id.syllabus_limit and len(chk_running_bk) >= self.card_id.book_limit:
                self.card_id = ''
                return {
                    'warning': {
                        'title': _('Thẻ thư viện'),
                        'message': _('Bạn đã mượn đủ số lượng tài liệu được phép.\nKhông thể mượn thêm tài liệu cho thẻ này!'),
                    }
                }
            elif len(chk_running_bk) >= self.card_id.book_limit or len(chk_running_syl) >= self.card_id.syllabus_limit:
                return {
                    'warning': {
                        'title': _('Thẻ thư viện'),
                        'message': _('Số tài liệu tham khảo: %s\nSố giáo trình: %s\nBạn đang mượn %s tài liệu tham khảo và %s giáo trình!')
                                   % (self.card_id.book_limit,  self.card_id.syllabus_limit, len(chk_running_bk), len(chk_running_syl)),
                    }
                }

    @api.constrains('book_id', 'meta_book_id', 'project_id', 'meta_project_id')
    def _constrains_doc_meta_doc(self):
        if self.book_id != self.meta_book_id.book_id:
            raise ValidationError(_('Hãy chọn lại meta sách!'))
        elif self.project_id != self.meta_project_id.project_id:
            raise ValidationError(_('Hãy chọn lại meta đồ án - luận văn!'))

    @api.onchange('meta_book_id', 'meta_project_id')
    def _onchange_meta_book_id(self):
        if self.book_id:
            return {'domain': {'meta_book_id': [('book_id', '=', self.book_id.id), ('state', '=', 'available')]}}
        elif self.project_id:
            return {'domain': {'meta_project_id': [('project_id', '=', self.project_id.id), ('state', '=', 'available')]}}

    @api.constrains('card_id', 'book_id', 'project_id')
    def _constrains_card_id_book_project(self):
        lib_checkout = self.env['lib.checkout.back.home']
        domain = [('card_id', '=', self.card_id.id),
                  ('state', 'in', ['running', 'draft']),
                  ('book_id', '=', self.book_id.id),
                  ('project_id', '=', self.project_id.id),
                  ('id', 'not in', self.ids)]
        chk_of_card = lib_checkout.sudo().search(domain)
        if chk_of_card:
            raise ValidationError(_('Bạn không thể mượn tài liệu giống nhau!'))

    @api.onchange('type_document')
    def onchange_type_document(self):
        if self.type_document == 'project':
            self.book_id = ''
            self.meta_book_id = ''
        elif self.type_document == 'book':
            self.project_id = ''
            self.meta_project_id = ''

    @api.onchange('return_date')
    def _onchange_return_date(self):
        current_date = datetime.now()
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        if self.return_date and self.document_term and (self.return_date > (date_today + rd(days=self.document_term)).date()):
            self.return_date = ''
            return {
                       'warning': {
                           'title': _('Thời hạn mượn tài liệu'),
                           'message': _('Vượt quá thời hạn trả sách!')
                       }
                   }
        # if self.return_date and self.return_date < date_today.date():
        #     self.return_date = ''
        #     return {
        #                'warning': {
        #                    'title': _('Duration Borrow Document'),
        #                    'message': _('Ngày hẹn trả phải lớn hơn ngày hiện tại!'),
        #                }
        #            }
        if self.return_date and self.end_date and self.return_date > self.end_date:
            self.return_date = ''
            return {
                'warning': {
                    'title': _('Thẻ thư viện'),
                    'message': _('Vượt quá thời hạn của thẻ thư viện!'),
                }
            }

    @api.constrains('return_date', 'end_date')
    def constrains_return_date_end_date(self):
        for chk in self:
            if chk.return_date and chk.end_date and chk.return_date > chk.end_date:
                raise ValidationError(_('Vượt quá thời hạn của thẻ thư viện!'))

    @api.onchange('book_id')
    def _onchange_book_id(self):
        self.meta_book_id = ''
        return {'domain': {'meta_book_id': [('state', '=', 'available'),
                                            ('book_id', '=', self.book_id.id)]}}

    @api.onchange('project_id')
    def _onchange_project_id(self):
        self.meta_project_id = ''
        return {'domain': {'meta_project_id': [('state', '=', 'available'),
                                               ('project_id', '=', self.project_id.id)]}}

    @api.depends('meta_book_id', 'book_id', 'meta_project_id', 'project_id')
    def _compute_status_document_doc_price(self):
        for chk in self:
            if chk.meta_book_id:
                chk.status_document = chk.meta_book_id.description
                chk.doc_price = chk.book_id.price
                chk.document_term = chk.book_id.book_term
            elif chk.meta_project_id:
                chk.status_document = chk.meta_project_id.description
                chk.doc_price = chk.project_id.price
                chk.document_term = chk.project_id.project_term

    # @api.depends('book_id', 'project_id')
    # def _compute_category_doc(self):
    #     for chk in self:
    #         if chk.book_id:
    #             chk.category_doc = chk.book_id.category.name
    #         elif chk.project_id:
    #             chk.category_doc = chk.project_id.major_id.name

    # def unlink(self):
    #     for chk in self:
    #         if chk.state != 'draft':
    #             raise ValidationError(_('You can not delete checkout when state not is draft!'))
    #     return super(CheckoutBackHome, self).unlink()

    @api.onchange('state')
    def _onchange_state(self):
        current_date = datetime.now()
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz).date()
        if self.state == 'draft':
            self.update({
                'borrow_date': '',
                'return_date': '',
                'actual_return_date': '',
                'day_overdue': '',
                'penalty_doc_price': '',
                'penalty_chk_price': '',
                'penalty_total': '',
                'note': '',
            })
        elif self.state == 'done':
            self.actual_return_date = fields.Datetime.now()
            self.update({
                'day_overdue': '',
                'penalty_doc_price': '',
                'penalty_chk_price': '',
                'penalty_total': '',
                'note': '',
            })
        elif self.state == 'fined':
            self.day_overdue = (date_today - self.return_date).days if self.return_date < date_today else 0
            self.penalty_chk_price = self.day_overdue * 1000
            self.actual_return_date = fields.Datetime.now()
            self.penalty_doc_price = 0
            self.note = ''
        elif self.state == 'lost':
            self.day_overdue = (date_today - self.return_date).days if self.return_date < date_today else 0
            self.penalty_chk_price = self.day_overdue * 1000
            self.penalty_doc_price = self.doc_price
            self.actual_return_date = fields.Datetime.now()
        self.kanban_state = 'normal'

    def running_state(self):
        syll_cate = self.env.ref('do_an_tn.data_category_6').id
        state_running = self.env['lib.checkout.stage'].search([('state', '=', 'running')])
        for chk in self:
            chk_running_syl = self.sudo().search([('card_id', '=', chk.card_id.id),
                                           ('state', '=', 'running'),
                                           ('id', 'not in', chk.ids),
                                           ('type_document', '=', 'book'),
                                           ('category_doc', '=', syll_cate)])
            chk_running_bk = self.sudo().search([('card_id', '=', chk.card_id.id),
                                          ('state', '=', 'running'),
                                          ('id', 'not in', chk.ids),
                                          ('category_doc', '!=', syll_cate)])
            if len(chk_running_bk) >= chk.card_id.book_limit and len(chk_running_syl) >= chk.card_id.syllabus_limit:
                raise ValidationError(_('Không thể mượn thêm tài liệu'))
            elif len(chk_running_bk) >= chk.card_id.book_limit:
                if self.category_doc.id != syll_cate:
                    raise ValidationError(_('Không thể mượn thêm tài liệu tham khảo!'))
            elif len(chk_running_syl) >= chk.card_id.syllabus_limit:
                if self.category_doc.id == syll_cate:
                    raise ValidationError(_('Không thể mượn thêm giáo trình!'))
            chk.name_seq = self.env['ir.sequence'].next_by_code('lib.checkout.sequence') or _('New')
            chk.stage_id = state_running
            if chk.book_id:
                if not chk.meta_book_id:
                    raise ValidationError(_('Hãy chọn lại meta sách!'))
                if chk.meta_book_id.state == 'available':
                    chk.meta_book_id.write({
                        'state': 'not_available',
                        'checkout': str(chk.name_get()[0][1]) + _(' - Mượn về'),
                    })
                    chk.book_id._compute_quantity_remaining()
                else:
                    raise ValidationError(_('Sách: "%s - %s" đã được mượn.' %
                                            (str(self.meta_book_id.name_seq), str(self.meta_book_id.book_id.name))))
            elif chk.project_id:
                if not chk.meta_project_id:
                    raise ValidationError(_('Hãy chọn lại meta đồ án - luận văn!'))
                if chk.meta_project_id.state == 'available':
                    chk.meta_project_id.write({
                        'state': 'not_available',
                        'checkout': str(chk.name_get()[0][1]) + _(' - Mượn về'),
                    })
                    chk.project_id._compute_quantity_remaining()
                else:
                    raise ValidationError(_('Đồ án - luận văn: " %s " đã được mượn.' % (str(self.project_id.name))))
            chk.borrow_date = fields.Datetime.now()

    @api.multi
    def draft_state(self):
        stage_draft = self.env['lib.checkout.stage'].search([('state', '=', 'draft')])
        for chk in self:
            chk.stage_id = stage_draft
            chk._onchange_state()
            if chk.book_id and chk.meta_book_id.state == 'not_available':
                chk.meta_book_id.write({
                    'state': 'available',
                    'checkout': '',
                })
                chk.book_id._compute_quantity_remaining()
            elif chk.project_id and chk.meta_project_id.state == 'not_available':
                chk.meta_project_id.write({
                    'state': 'available',
                    'checkout': '',
                })
                chk.project_id._compute_quantity_remaining()

    @api.multi
    def done_state(self):
        Stages = self.env['lib.checkout.stage']
        stage_done = Stages.search([('state', '=', 'done')])
        stage_fined = Stages.search([('state', '=', 'fined')])
        for chk in self:
            if chk.return_date >= fields.Date.today():
                chk.stage_id = stage_done
                chk._onchange_state()
                if chk.book_id and chk.meta_book_id.state == 'not_available':
                    chk.meta_book_id.write({
                        'state': 'available',
                        'checkout': '',
                    })
                    chk.book_id._compute_quantity_remaining()
                elif chk.project_id and chk.meta_project_id.state == 'not_available':
                    chk.meta_project_id.write({
                        'state': 'available',
                        'checkout': '',
                    })
                    chk.project_id._compute_quantity_remaining()
            elif chk.return_date < fields.Date.today():
                chk.stage_id = stage_fined
                chk._onchange_state()
                if chk.book_id and chk.meta_book_id.state == 'not_available':
                    chk.meta_book_id.write({
                        'state': 'available',
                        'checkout': '',
                    })
                    chk.book_id._compute_quantity_remaining()
                elif chk.project_id and chk.meta_project_id.state == 'not_available':
                    chk.meta_project_id.write({
                        'state': 'available',
                        'checkout': '',
                    })
                    chk.project_id._compute_quantity_remaining()

    def fined_state(self):
        stage_fined = self.env['lib.checkout.stage'].search([('state', '=', 'fined')])
        for chk in self:
            chk.stage_id = stage_fined
            chk._onchange_state()
            if chk.book_id and chk.meta_book_id.state == 'not_available':
                chk.meta_book_id.write({
                    'state': 'available',
                    'checkout': '',
                })
                chk.book_id._compute_quantity_remaining()
            elif chk.project_id and chk.meta_project_id.state == 'not_available':
                chk.meta_project_id.write({
                    'state': 'available',
                    'checkout': '',
                })
                chk.project_id._compute_quantity_remaining()
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'lib.checkout.back.home',
                'res_id': chk.id,
                'context': context,
                'target': 'current',
            }

    @api.multi
    def lost_document(self):
        stage_lost = self.env['lib.checkout.stage'].search([('state', '=', 'lost')])
        for chk in self:
            chk.stage_id = stage_lost
            chk._onchange_state()
            dic = {
                    'is_lost': True,
                    'checkout': str(chk.name_get()[0][1]) + _(' - Mượn về'),
                    'state': 'not_available',
                }
            if chk.book_id:
                chk.meta_book_id.write(dic)
                chk.book_id._compute_quantity_remaining()
                chk.note = _('Mất tài liệu: %s') % (str(chk.meta_book_id.name_seq))
            elif chk.project_id:
                chk.meta_project_id.write(dic)
                chk.project_id._compute_quantity_remaining()
                chk.note = _('Mất tài liệu: %s') % (str(chk.meta_project_id.name_seq))

    def cancel_state(self):
        Stages = self.env['lib.checkout.stage']
        stage_fined = Stages.search([('state', '=', 'fined')])
        stage_lost = Stages.search([('state', '=', 'lost')])
        stage_done = Stages.search([('state', '=', 'done')])
        for chk in self:
            if chk.stage_id == stage_lost:
                chk.stage_id = stage_fined
                chk._onchange_state()
                if chk.book_id and chk.meta_book_id.state == 'not_available':
                    chk.meta_book_id.write({
                        'state': 'available',
                        'checkout': '',
                        'is_lost': False,
                    })
                    chk.book_id._compute_quantity_remaining()
                elif chk.project_id and chk.meta_project_id.state == 'not_available':
                    chk.meta_project_id.write({
                        'state': 'available',
                        'checkout': '',
                        'is_lost': False,
                    })
                    chk.project_id._compute_quantity_remaining()
                context = dict(self.env.context)
                context['form_view_initial_mode'] = 'edit'
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'lib.checkout.back.home',
                    'res_id': chk.id,
                    'context': context
                }
            if chk.stage_id == stage_fined:
                if self.return_date >= fields.Date.today():
                    chk.stage_id = stage_done
                    chk._onchange_state()
                else:
                    if chk.book_id:
                        chk.meta_book_id.write({
                            'description': chk.status_document
                        })
                    elif chk.project_id:
                        chk.meta_project_id.write({
                            'description': chk.status_document
                        })
                    chk.penalty_doc_price = 0
                    chk.note = ''

    @api.depends('penalty_chk_price', 'penalty_doc_price')
    def _compute_penalty_total(self):
        for chk in self:
            chk.penalty_total = chk.penalty_chk_price + chk.penalty_doc_price

    def _compute_count_chk_bh(self):
        syll_cate = self.env.ref('do_an_tn.data_category_6').id
        for chk in self:
            chk_hb = self.sudo().search([('card_id', '=', chk.card_id.id),
                                         ('state', '=', 'running')])
            chk.count_syl = len(chk_hb.filtered(lambda a: a.category_doc.id == syll_cate))
            chk.count_doc = len(chk_hb) - chk.count_syl
            chk.count_penalty = len(self.sudo().search([('card_id', '=', chk.card_id.id),
                                                        ('state', 'in', ['fined', 'lost'])]))

            chk.count_waiting = self.search_count([('state', '=', 'draft'),
                                                   ('book_id', '=', self.book_id.id),
                                                   ('project_id', '=', self.project_id.id)])

    @api.multi
    def open_chk_document(self):
        syll_cate = self.env.ref('do_an_tn.data_category_6').id
        return {
            'name': _('Phiếu mượn tài liệu tham khảo'),
            'domain': [('card_id', '=', self.card_id.id),
                       ('state', '=', 'running'),
                       ('category_doc', '!=', syll_cate)],
            'view_type': 'form',
            'res_model': 'lib.checkout.back.home',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def open_chk_syllabus(self):
        syll_cate = self.env.ref('do_an_tn.data_category_6').id
        return {
            'name': _('Phiếu mượn giáo trình'),
            'domain': [('card_id', '=', self.card_id.id),
                       ('state', '=', 'running'),
                       ('type_document', '=', 'book'),
                       ('category_doc', '=', syll_cate)],
            'view_type': 'form',
            'res_model': 'lib.checkout.back.home',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def open_all_checkout_bh(self):
        return {
            'name': _('Tất cả phiếu mượn đang hoạt động'),
            'domain': [('card_id', '=', self.card_id.id),
                       ('state', '=', 'running')],
            'view_type': 'form',
            'res_model': 'lib.checkout.back.home',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def open_all_penalty_checkout(self):
        return {
            'name': _('Phiếu mượn bị phạt'),
            'domain': [('card_id', '=', self.card_id.id),
                       ('state', 'in', ['fined', 'lost'])],
            'view_type': 'form',
            'res_model': 'lib.checkout.back.home',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def library_chk_bh_check_ret_date(self):
        current_date = datetime.now()
        print('Hoạt động theo lịch trình: Kiểm tra ngày hẹn trả tài liệu: Mượn về!')
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        CheckoutBH = self.sudo().search([('state', '=', 'running'),
                                         ('return_date', '<', date_today)])
        print(CheckoutBH)
        template_id = self.env.ref('do_an_tn.scheduled_send_mail_chk_overdue').id
        template = self.env['mail.template'].browse(template_id)
        for chk in CheckoutBH:
            chk.day_overdue = (date_today.date() - chk.return_date).days if chk.return_date < date_today.date() else 0
            if chk.kanban_state != 'overdue':
                template.send_mail(chk.id, force_send=True, raise_exception=True)
                chk.message_post(_('Đã gửi email thông báo mượn quá hạn cho độc giả!'))
                chk.kanban_state = 'overdue'

    @api.multi
    def open_checkout_waiting(self):
        return {
            'name': _('Tất cả phiếu mượn đang chờ'),
            'domain': [('state', '=', 'draft'),
                       ('book_id', '=', self.book_id.id),
                       ('project_id', '=', self.project_id.id)],
            'view_type': 'form',
            'res_model': 'lib.checkout.back.home',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }






