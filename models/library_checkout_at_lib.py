from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
import pytz


class CheckoutAtLib(models.Model):
    _name = 'lib.checkout.at.lib'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Phiếu mượn tại thư viện'

    @api.model
    def _default_stage(self):
        return self.env['lib.checkout.stage'].search([], limit=1)

    @api.model
    def _group_expand_stage_id(self, stages, domain, order):
        return stages.search([], order=order)

    name_seq = fields.Char(string="Mã phiếu mượn", default=lambda self: _('New'), readonly=True)
    card_id = fields.Many2one('lib.card', string="Mã thẻ mượn",
                              required=True,
                              domain=[('state', '=', 'running'), ('is_penalty', '=', False)], track_visibility='always')
    state_card = fields.Selection(related='card_id.state', store=True, string='Trạng thái thẻ mượn')
    gt_name = fields.Char(related='card_id.gt_name', store=True, track_visibility='always', string='Tên độc giả')
    stage_id = fields.Many2one('lib.checkout.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               track_visibility='always'
                               )
    state = fields.Selection(related='stage_id.state', store=True, string='Trạng thái phiếu mượn')
    type_document = fields.Selection([
        ('book', 'Sách'),
        ('magazine', 'Tạp chí - báo'),
        ('project', 'Đồ án - luận văn'),
    ], string='Loại tài liệu', default='book', required=True)
    book_id = fields.Many2one('lib.book', 'Tiêu đề sách')
    meta_book_id = fields.Many2one('lib.meta.books', string='Meta Sách')
    project_id = fields.Many2one('lib.document.project', 'Tên đồ án')
    meta_project_id = fields.Many2one('lib.meta.projects', string='Meta đồ án')
    mgz_new_id = fields.Many2one('lib.magazine.newspaper', 'Tạp chí - báo', track_visibility='always')
    meta_mgz_new_id = fields.Many2one('lib.meta.magazinenewspapers',
                                      string='Meta tạp chí - báo', track_visibility='always')
    status_document = fields.Text('Tình trạng', compute='_compute_status_document', store=True)
    doc_price = fields.Monetary("Giá tiền", 'currency_id', compute='_compute_doc_price', store=True)
    currency_id = fields.Many2one('res.currency', 'Tiền tệ',
                                  default=lambda s: s.env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1))
    penalty_price = fields.Monetary('Tiền phạt', 'currency_id')
    note = fields.Char('Ghi chú')
    user_id = fields.Many2one('res.users', 'Nhân viên thư viện',
                              default=lambda s: s.env.uid,
                              readonly=True, track_visibility='always', required=True)
    borrow_date = fields.Datetime(string='Ngày mượn', track_visibility='always')
    return_date = fields.Datetime(string='Ngày trả', track_visibility='always')
    count_waiting = fields.Integer(compute='_compute_count_waiting')

    @api.multi
    def print_penalty_report(self):
        return self.env.ref('do_an_tn.report_penalty_checkout_at_lib_xls').report_action(self)

    @api.constrains('book_id', 'meta_book_id', 'project_id', 'meta_project_id', 'mgz_new_id', 'meta_mgz_new_id')
    def _constrains_doc_meta_doc(self):
        if self.book_id != self.meta_book_id.book_id:
            raise ValidationError(_('Chọn lại meta sách!'))
        elif self.mgz_new_id != self.meta_mgz_new_id.mgz_new_id:
            raise ValidationError(_('Chọn lại meta tạp chí - báo!'))
        elif self.project_id != self.meta_project_id.project_id:
            raise ValidationError(_('Chọn lại meta đồ án - luận văn!'))

    @api.onchange('meta_book_id', 'meta_project_id', 'meta_mgz_new_id')
    def _onchange_meta_book_id(self):
        if self.book_id:
            return {'domain': {'meta_book_id': [('book_id', '=', self.book_id.id), ('state', '=', 'available')]}}
        elif self.mgz_new_id:
            return {'domain': {'meta_mgz_new_id': [('mgz_new_id', '=', self.mgz_new_id.id), ('state', '=', 'available')]}}
        elif self.project_id:
            return {'domain': {'meta_project_id': [('project_id', '=', self.project_id.id), ('state', '=', 'available')]}}

    @api.onchange('card_id')
    def onchange_card_id(self):
        if self.sudo().search([('card_id', '=', self.card_id.id),
                               ('state', '=', 'running'),
                               ('id', 'not in', self.ids)]):
            self.card_id = ''
            return {
                'warning': {
                    'title': _('Thẻ thư viện'),
                    'message': _('Bạn đang mượn một tài liệu, vui lòng trả lại để tiếp tục!'),
                }
            }

    @api.onchange('type_document')
    def onchange_type_document(self):
        if self.type_document == 'project':
            self.book_id = ''
            self.meta_book_id = ''
            self.mgz_new_id = ''
            self.meta_mgz_new_id = ''
        elif self.type_document == 'book':
            self.project_id = ''
            self.meta_project_id = ''
            self.mgz_new_id = ''
            self.meta_mgz_new_id = ''
        else:
            self.book_id = ''
            self.meta_book_id = ''
            self.project_id = ''
            self.meta_project_id = ''

    @api.depends('book_id', 'mgz_new_id', 'project_id')
    def _compute_doc_price(self):
        for chk in self:
            if chk.book_id:
                chk.doc_price = chk.book_id.price
            elif chk.mgz_new_id:
                chk.doc_price = chk.mgz_new_id.price
            elif chk.project_id:
                chk.doc_price = chk.project_id.price

    @api.onchange('book_id')
    def _onchange_book_id(self):
        self.meta_book_id = ''
        return {'domain': {'meta_book_id': [('state', '=', 'available'),
                                            ('book_id', '=', self.book_id.id)]}}

    @api.onchange('mgz_new_id')
    def _onchange_mgz_new_id(self):
        self.meta_mgz_new_id = ''
        return {'domain': {'meta_mgz_new_id': [('state', '=', 'available'),
                                               ('mgz_new_id', '=', self.mgz_new_id.id)]}}

    @api.onchange('project_id')
    def _onchange_project_id(self):
        self.meta_project_id = ''
        return {'domain': {'meta_project_id': [('state', '=', 'available'),
                                               ('project_id', '=', self.project_id.id)]}}

    @api.depends('meta_book_id', 'meta_mgz_new_id', 'meta_project_id')
    def _compute_status_document(self):
        for chk in self:
            if chk.meta_book_id:
                chk.status_document = chk.meta_book_id.description
            elif chk.meta_mgz_new_id:
                chk.status_document = chk.meta_mgz_new_id.description
            elif chk.meta_project_id:
                chk.status_document = chk.meta_project_id.description

    @api.constrains('card_id', 'book_id', 'mgz_new_id', 'project_id')
    def _constrains_card_id_book(self):
        lib_checkout = self.env['lib.checkout.at.lib']
        domain = [('card_id', '=', self.card_id.id),
                  ('state', 'in', ['running', 'draft']),
                  ('book_id', '=', self.book_id.id),
                  ('mgz_new_id', '=', self.mgz_new_id.id),
                  ('project_id', '=', self.project_id.id),
                  ('id', 'not in', self.ids)]
        chk_of_card = lib_checkout.sudo().search(domain)
        if chk_of_card:
            raise ValidationError(_('Bạn không thể mượn tài liệu giống nhau!'))

        domain2 = [
            ('card_id', '=', self.card_id.id),
            ('state', '=', 'running'),
            ('id', '!=', self.id)
        ]
        checkout_of_card2 = lib_checkout.sudo().search_count(domain2)
        if checkout_of_card2:
            raise ValidationError(_('Bạn đã mượn nhiều hơn số lượng sách được chỉ định cho mỗi thẻ'))

    @api.onchange('state')
    def _onchange_state(self):
        if self.state == 'draft':
            self.borrow_date = ''
            self.return_date = ''
        elif self.state == 'running':
            self.return_date = ''
        if self.state not in ['lost']:
            self.penalty_price = 0
            self.note = ''

    @api.multi
    def running_state(self):
        state_running = self.env['lib.checkout.stage'].search([('state', '=', 'running')])
        for chk in self:
            if self.sudo().search([('card_id', '=', chk.card_id.id),
                            ('state', '=', 'running'),
                            ('id', 'not in', self.ids)]):
                raise ValidationError(_('Bạn đang mượn một tài liệu, vui lòng trả lại để tiếp tục!'))
            chk.name_seq = self.env['ir.sequence'].next_by_code('lib.checkout.sequence') or _('New')
            chk.stage_id = state_running
            chk._onchange_state()
            if chk.book_id:
                if not chk.meta_book_id:
                    raise ValidationError(_('Hãy chọn lại meta sách!'))
                if chk.meta_book_id.state == 'available':
                    chk.meta_book_id.state = 'not_available'
                    chk.book_id._compute_quantity_remaining()
                    chk.meta_book_id.checkout = str(chk.name_get()[0][1]) + _(' - tại thư viện')
                else:
                    raise ValidationError(_('Sách: "%s - %s" đã được mượn.' %
                                          (self.meta_book_id.name_seq, self.book_id.name)))
            elif chk.mgz_new_id:
                if not chk.meta_mgz_new_id:
                    raise ValidationError(_('Hãy chọn lại meta tạp chí - báo!'))
                if chk.meta_mgz_new_id.state == 'available':
                    chk.meta_mgz_new_id.state = 'not_available'
                    chk.mgz_new_id._compute_quantity_remaining()
                    chk.meta_mgz_new_id.checkout = str(chk.name_get()[0][1]) + _(' - tại thư viện')
                else:
                    raise ValidationError(_('Tạp chí - báo đã được mượn!'))
            elif chk.project_id:
                if not chk.meta_project_id:
                    raise ValidationError(_('Hãy chọn lại meta đồ án - luận văn!'))
                if chk.meta_project_id.state == 'available':
                    chk.meta_project_id.state = 'not_available'
                    chk.project_id._compute_quantity_remaining()
                    chk.meta_project_id.checkout = str(chk.name_get()[0][1]) + _(' - tại thư viện')
                else:
                    raise ValidationError(_('Đồ án - luận văn: " %s " đã được mượn.' % (self.project_id.name)))
            chk.borrow_date = fields.Datetime.now()
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': _('Phiếu mượn đã được xác nhận'),
                    'type': 'rainbow_man',
                }
            }

    @api.multi
    def draft_state(self):
        stage_draft = self.env['lib.checkout.stage'].search([('state', '=', 'draft')])
        for chk in self:
            chk.stage_id = stage_draft
            chk._onchange_state()
            dic = {
                'state': 'available',
                'checkout': '',
            }
            if chk.book_id and chk.meta_book_id.state == 'not_available':
                chk.meta_book_id.write(dic)
                chk.book_id._compute_quantity_remaining()
            elif chk.mgz_new_id and chk.meta_mgz_new_id.state == 'not_available':
                chk.meta_mgz_new_id.write(dic)
                chk.mgz_new_id._compute_quantity_remaining()
            elif chk.project_id and chk.meta_project_id.state == 'not_available':
                chk.meta_project_id.write(dic)
                chk.project_id._compute_quantity_remaining()

    @api.multi
    def done_state(self):
        stage_done = self.env['lib.checkout.stage'].search([('state', '=', 'done')])
        for chk in self:
            chk.stage_id = stage_done
            chk._onchange_state()
            dic = {
                'state': 'available',
                'checkout': '',
            }
            if chk.book_id:
                chk.meta_book_id.write(dic)
                chk.book_id._compute_quantity_remaining()
            elif chk.mgz_new_id:
                chk.meta_mgz_new_id.write(dic)
                chk.mgz_new_id._compute_quantity_remaining()
            elif chk.project_id:
                chk.meta_project_id.write(dic)
                chk.project_id._compute_quantity_remaining()
            chk.return_date = fields.Datetime.now()

    @api.multi
    def fined_state(self):
        stage_fined = self.env['lib.checkout.stage'].search([('state', '=', 'fined')])
        for chk in self:
            chk.stage_id = stage_fined
            chk._onchange_state()
            dic = {
                'state': 'available',
                'checkout': '',
            }
            if chk.book_id:
                chk.meta_book_id.write(dic)
                chk.book_id._compute_quantity_remaining()
            elif chk.mgz_new_id:
                chk.meta_mgz_new_id.write(dic)
                chk.mgz_new_id._compute_quantity_remaining()
            elif chk.project_id:
                chk.meta_project_id.write(dic)
                chk.project_id._compute_quantity_remaining()
            chk.return_date = fields.Datetime.now()
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'lib.checkout.at.lib',
                'context': context,
                'target': 'current',
                'res_id': chk.id,
            }

    @api.multi
    def lost_document(self):
        stage_lost = self.env['lib.checkout.stage'].search([('state', '=', 'lost')])
        for chk in self:
            chk.stage_id = stage_lost
            chk._onchange_state()
            dic = {
                'is_lost': True,
                'checkout': str(chk.name_get()[0][1]) + _(' - tại thư viện'),
                'state': 'not_available',
            }
            if chk.book_id:
                chk.meta_book_id.write(dic)
                chk.book_id._compute_quantity_remaining()
                chk.note = _('Mất tài liệu: %s') % (str(chk.meta_book_id.name_seq))
            elif chk.mgz_new_id:
                chk.meta_mgz_new_id.write(dic)
                chk.mgz_new_id._compute_quantity_remaining()
                chk.note = _('Mất tài liệu: %s') % (str(chk.meta_mgz_new_id.name_seq))
            elif chk.project_id:
                chk.meta_project_id.write(dic)
                chk.project_id._compute_quantity_remaining()
                chk.note = _('Mất tài liệu: %s') % (str(chk.meta_project_id.name_seq))
            chk.return_date = fields.Datetime.now()
            chk.penalty_price = chk.doc_price

    @api.multi
    def cancel_state(self):
        stage_done = self.env['lib.checkout.stage'].search([('state', '=', 'done')])
        for chk in self:
            chk.stage_id = stage_done
            chk._onchange_state()
            dic = {
                'state': 'available',
                'checkout': '',
                'description': chk.status_document,
                'is_lost': False,
            }
            if chk.book_id:
                chk.meta_book_id.write(dic)
                chk.book_id._compute_quantity_remaining()
            elif chk.mgz_new_id:
                chk.meta_mgz_new_id.write(dic)
                chk.mgz_new_id._compute_quantity_remaining()
            elif chk.project_id:
                chk.meta_project_id.write(dic)
                chk.project_id._compute_quantity_remaining()
            chk.return_date = fields.Datetime.now()

    def borrow_back_home(self):
        chk_bh_obj = self.env['lib.checkout.back.home']
        for chk in self:
            if chk.type_document == 'magazine':
                raise ValidationError('Không thể mượn tạp chí - báo về nhà')
            else:
                vals={}
                vals.update({
                    'card_id': chk.card_id.id,
                    'type_document': chk.type_document,
                })
                if chk.book_id:
                    vals.update({
                        'book_id': chk.book_id.id,
                        'meta_book_id': chk.meta_book_id.id,
                    })
                elif chk.project_id:
                    vals.update({
                        'project_id': chk.project_id.id,
                        'meta_project_id': chk.meta_project_id.id,
                    })
            chk_bh = chk_bh_obj.create(vals)
            return {'name': _('Phiếu mượn về'),
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_id': chk_bh.id,
                    'res_model': 'lib.checkout.back.home',
                    'type': 'ir.actions.act_window',
                    'target': 'new'}

    @api.multi
    def name_get(self):
        res = []
        for chk in self:
            res.append((chk.id, '%s - %s' % (chk.name_seq, chk.gt_name)))
        return res

    @api.multi
    def print_report(self):
        return self.env.ref('do_an_tn.action_library_checkout_at_lib_penalty').report_action(self)

    @api.multi
    def open_checkout_waiting(self):
        return {
            'name': _('Phiếu mượn đang chờ'),
            'domain': [('state', '=', 'draft'),
                       ('book_id', '=', self.book_id.id),
                       ('mgz_new_id', '=', self.mgz_new_id.id),
                       ('project_id', '=', self.project_id.id)],
            'view_type': 'form',
            'res_model': 'lib.checkout.at.lib',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def _compute_count_waiting(self):
        for chk in self:
            chk.count_waiting = self.search_count([('state', '=', 'draft'),
                                                   ('book_id', '=', chk.book_id.id),
                                                   ('mgz_new_id', '=', chk.mgz_new_id.id),
                                                   ('project_id', '=', chk.project_id.id)])

    def unlink(self):
        for chk in self:
            if chk.state != 'draft':
                raise ValidationError(_('Không thể xóa phiếu khác trạng thái \'Nháp\'!'))
        return super(CheckoutAtLib, self).unlink()


