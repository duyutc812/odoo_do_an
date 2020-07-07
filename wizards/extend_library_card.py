from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta as rd
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import pytz


class ModifyEmailCard(models.TransientModel):
    _name = 'modify.email.on.card'
    _description = 'Modify Email On Card'

    email = fields.Char('Email')

    @api.multi
    def button_modify_email_on_card(self):
        card = self.env['lib.card'].sudo().search([('id', '=', self.env.context.get('active_id'))])
        card.email = self.email
        return True


class ExtendLibraryCard(models.TransientModel):
    _name = 'extend.lib.card'
    _description = 'Extend Library Card'

    card_id = fields.Many2one('lib.card', string="Card ID")
    duration_id = fields.Many2one('lib.duration', string='Duration')
    currency_id = fields.Many2one('res.currency', 'Currency', related='duration_id.currency_id', store=True)
    price = fields.Monetary('Price', 'currency_id', related='duration_id.price')

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        card = self.env['lib.card'].sudo().search([('id', '=', self.env.context.get('active_id'))])
        defaults['card_id'] = card.id
        defaults['duration_id'] = card.duration_id.id
        return defaults

    @api.multi
    def button_extend_card(self):
        self.card_id.end_date += rd(months=int(self.duration_id.duration))
        self.card_id.price += self.price
        self.card_id.message_post(_('Card ID: %s of %s has been extended about %s months' % (self.card_id.code, self.card_id.gt_name, self.duration_id.duration)))
        return True


class ExtendLibraryCheckoutBackHome(models.TransientModel):
    _name = 'extend.checkout.bh'
    _description = 'Extend Checkout Back Home'

    checkout_id = fields.Many2one('lib.checkout.back.home', string="Checkout ID", readonly=True)
    extend_date = fields.Date(string='Extend date to :')

    @api.model
    def default_get(self, field_names):
        current_date = datetime.now()
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        defaults = super().default_get(field_names)
        chk = self.env['lib.checkout.back.home'].sudo().search([('id', '=', self.env.context.get('active_id'))])
        defaults['checkout_id'] = chk.id
        if chk.return_date < date_today.date():
            raise ValidationError(_('Cannot extend checkout!'))
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
        if self.extend_date > (date_today + rd(days=self.checkout_id.document_term)).date():
            raise ValidationError(_('Exceeded deadline for returning books!'))
        if self.extend_date > self.checkout_id.end_date:
            raise ValidationError(_('Exceeded term of library card!'))
        if self.extend_date and self.extend_date <= date_today.date():
            raise ValidationError(_('The return appointment date must be great than current date!'))
        self.checkout_id.return_date = self.extend_date
        self.checkout_id.message_post(_('Checkout ID: %s of %s has been extended to %s' % (self.checkout_id.name_seq, self.checkout_id.gt_name, self.extend_date.strftime("%d-%m-%Y"))))
        return True
