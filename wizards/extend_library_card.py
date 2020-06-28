from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta as rd


class ExtendLibraryCard(models.TransientModel):
    _name = 'extend.library.card'
    _description = 'Extend Library Card'

    card_id = fields.Many2one('library.card', string="Card ID")
    duration_id = fields.Many2one('library.duration', string='Duration')
    currency_id = fields.Many2one('res.currency', 'Currency', related='duration_id.currency_id', store=True)
    price = fields.Monetary('Price', 'currency_id', related='duration_id.price')

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        card = self.env['library.card'].search([('id', '=', self.env.context.get('active_id'))])
        defaults['card_id'] = card.id
        defaults['duration_id'] = card.duration_id.id
        return defaults

    @api.multi
    def button_extend_card(self):
        self.card_id.end_date += rd(months=int(self.duration_id.duration))
        self.card_id.price += self.price
        self.card_id.message_post(_('Card ID: %s of %s has been extended about %s months' % (self.card_id.code, self.card_id.gt_name, self.duration_id.duration)))
        return True
