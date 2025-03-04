from odoo import api, exceptions, fields, models, _

import logging
_logger = logging.getLogger(__name__)


class CheckoutMassMessage(models.TransientModel):
    _name = 'lib.checkout.bh.send.email'
    _description = 'Gửi email cho độc giả mượn về'

    checkout_id = fields.Many2one(
        'lib.checkout.back.home',
        string='Mã phiếu')
    message_subject = fields.Char(default=_('Thư viện Trường Đại học ABC!'), string="Tiêu đề")
    message_body = fields.Text('Nội dung')
    email = fields.Char()

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        Checkout = self.env.context.get('active_id')
        chk = self.env['lib.checkout.back.home'].search([('id', '=', Checkout)])
        defaults['checkout_id'] = chk.id
        defaults['email'] = chk.card_id.email if chk.card_id.email else ''
        return defaults

    @api.multi
    def button_send(self):
        self.ensure_one()
        if not self.message_body:
            raise exceptions.UserError(
                'Nhập nội dung để có thể gửi!')
        if not self.message_subject:
            raise exceptions.UserError(
                'Nhập tiêu đề để có thể gửi!')
        if not self.email:
            raise exceptions.UserError(
                'Nhập email để có thể gửi.')
        self.checkout_id.message_post(
            body=self.message_body,
            subject=self.message_subject,
        )
        template_id = self.env.ref('do_an_tn.lib_checkout_send_by_email').id
        template = self.env['mail.template'].browse(template_id)
        template.send_mail(self.id, force_send=True, raise_exception=True)
        return True
