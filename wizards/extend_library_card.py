from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta as rd
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import pytz


class ModifyEmailCard(models.TransientModel):
    _name = 'modify.email.on.card'
    _description = 'Thay đổi email thẻ thư viện'

    email = fields.Char('Email')

    @api.multi
    def button_modify_email_on_card(self):
        card = self.env['lib.card'].sudo().search([('id', '=', self.env.context.get('active_id'))])
        card.email = self.email
        return True


class ExtendLibraryCard(models.TransientModel):
    _name = 'extend.lib.card'
    _description = 'Gia hạn thẻ thư viện'

    card_id = fields.Many2one('lib.card', string="Mã thẻ mượn")
    duration_id = fields.Many2one('lib.duration', string='Thời hạn')
    currency_id = fields.Many2one('res.currency', 'Tiền tệ', related='duration_id.currency_id', store=True)
    price = fields.Monetary('Giá tiền', 'currency_id', related='duration_id.price')

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        card = self.env['lib.card'].sudo().search([('id', '=', self.env.context.get('active_id'))])
        defaults['card_id'] = card.id
        defaults['duration_id'] = card.duration_id.id
        return defaults

    @api.multi
    def button_extend_card(self):
        if self.card_id.state == 'expire':
            chk_at_libs = self.env['lib.checkout.at.lib'].search([('state', '=', 'running'), ('card_id', '=', self.card_id.id)], limit=1)
            chk_back_homes = self.env['lib.checkout.back.home'].search([('state', '=', 'running'), ('card_id', '=', self.card_id.id)], limit=1)
            if chk_at_libs or chk_back_homes:
                raise ValidationError(
                    _('Đang tồn tại phiếu mượn của thẻ mượn này, vui lòng trả lại tài liệu đang mượn để có thể '
                      'thực hiện gia hạn thẻ mượn!'))
        if self.card_id.is_penalty:
            raise ValidationError(_('Không thể gia hạn cho thẻ bị phạt!'))
        self.card_id.end_date += rd(months=int(self.duration_id.duration))
        self.card_id.price += self.price
        self.card_id.message_post(_('Mã thẻ mượn: %s của %s đã được gia hạn thêm %s tháng' % (self.card_id.name_seq, self.card_id.gt_name, self.duration_id.duration)))
        return True


class ExtendLibraryCheckoutBackHome(models.TransientModel):
    _name = 'extend.checkout.bh'
    _description = 'Gia hạn phiếu mượn về'

    checkout_id = fields.Many2one('lib.checkout.back.home', string="Mã phiếu mượn", readonly=True)
    extend_date = fields.Date(string='Gia hạn tới ngày')

    @api.model
    def default_get(self, field_names):
        current_date = datetime.now()
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        defaults = super().default_get(field_names)
        chk = self.env['lib.checkout.back.home'].sudo().search([('id', '=', self.env.context.get('active_id'))])
        defaults['checkout_id'] = chk.id
        if chk.return_date < date_today.date():
            raise ValidationError(_('Không thể gia hạn phiếu mượn!'))
        # if chk.type_document == 'book':
        #     if chk.meta_book_id.state == 'not_available':
        #         raise ValidationError(_('Book: "%s - %s" have borrowed.' %
        #                                 (chk.meta_book_id.name_seq, chk.book_id.name)))
        #     if len(chk.book_id.meta_book_ids.filtered(
        #             lambda a: a.state == 'available' and not a.is_lost)) == 1:
        #         print(len(chk.book_id.meta_book_ids.filtered(
        #             lambda a: a.state == 'available' and not a.is_lost)))
        #     raise ValidationError(_('khong the gia han muon'))
        # if chk.type_document == 'project':
        #     if chk.meta_project_id.state == 'not_available':
        #         raise ValidationError(_('The project : %s has been borrowed' % (chk.project_id.name)))
        #     if len(chk.project_id.meta_project_ids.filtered(
        #             lambda a: a.state == 'available' and not a.is_lost)) == 1:
        #         print(len(chk.book_id.meta_book_ids.filtered(
        #             lambda a: a.state == 'available' and not a.is_lost)))
        #     raise ValidationError(_('khong the gia han muon'))
        return defaults

    @api.multi
    def button_extend_checkout(self):
        current_date = datetime.now()
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        if self.extend_date <= self.checkout_id.return_date:
            raise ValidationError(_('Ngày gia hạn phải lớn hơn ngày hẹn trả hiện tại của phiếu!'))
        if self.extend_date > (date_today + rd(days=self.checkout_id.document_term)).date():
            raise ValidationError(_('Vượt quá thời hạn trả sách!'))
        if self.extend_date > self.checkout_id.end_date:
            raise ValidationError(_('Vượt quá ngày hết hạn thẻ thư viện!'))
        if self.extend_date and self.extend_date <= date_today.date():
            raise ValidationError(_('Ngày gia hạn phải lớn hơn ngày hiện tại!'))
        self.checkout_id.return_date = self.extend_date
        self.checkout_id.message_post(_('Mã phiếu mượn: %s của %s đã được gia hạn tới ngày %s' % (self.checkout_id.name_seq, self.checkout_id.gt_name, self.extend_date.strftime("%d-%m-%Y"))))
        return True
