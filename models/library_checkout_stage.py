from odoo import fields, models


class CardStage(models.Model):
    _name = 'library.card.stage'
    _description = 'Card Stage'
    _order = 'sequence,name'

    name = fields.Char(translation=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    fold = fields.Boolean()
    state = fields.Selection(
        [('draft', 'Draft'),
         ('running', 'Confirm'),
         ('expire', 'Expire')],
        default='draft',
    )


class CheckoutStage(models.Model):
    _name = 'library.checkout.stage'
    _description = 'Checkout Stage'
    _order = 'sequence,name'

    name = fields.Char(translation=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    fold = fields.Boolean()
    state = fields.Selection(
        [('draft', 'Draft'),
         ('running', 'Borrowed'),
         ('done', 'Returned'),
         ('fined', 'Fined')],
        default='draft',
    )


