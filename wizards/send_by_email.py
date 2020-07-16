from odoo import api, exceptions, fields, models, _

import logging
_logger = logging.getLogger(__name__)


class CheckoutMassMessage(models.TransientModel):
    _name = 'lib.checkout.bh.send.email'
    _description = 'Send Email to Reader'

    checkout_id = fields.Many2one(
        'lib.checkout.back.home',
        string='Checkout')
    message_subject = fields.Char(default=_('Library School notice!'))
    message_body = fields.Text()
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
                'Write a message body to send.')
        if not self.message_subject:
            raise exceptions.UserError(
                'Write a subject to send.')
        if not self.email:
            raise exceptions.UserError(
                'Enter email to send.')
        self.checkout_id.message_post(
            body=self.message_body,
            subject=self.message_subject,
        )
        template_id = self.env.ref('do_an_tn.lib_checkout_send_by_email').id
        template = self.env['mail.template'].browse(template_id)
        template.send_mail(self.id, force_send=True, raise_exception=True)
        print('Send Email to : ', self.id)
        return True
