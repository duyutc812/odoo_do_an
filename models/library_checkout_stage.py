from odoo import fields, models


class CheckoutStage(models.Model):
    _name = 'lib.checkout.stage'
    _description = 'Checkout Stage'
    _order = 'sequence,name'

    name = fields.Char(translation=True)
    sequence = fields.Integer(default=10)
    is_active = fields.Boolean(default=True)
    is_fold = fields.Boolean()
    state = fields.Selection(
        [('draft', 'Draft'),
         ('running', 'Borrowed'),
         ('done', 'Returned'),
         ('fined', 'Fined'),
         ('lost', 'Lost'),
         ('cancel', 'Canceled')],
        default='draft',
    )


# class CheckoutInLIb(models.Model):
#     _name = 'checkout.stage.in.lib'
#     _description = 'Checkout Stage In Lib'
#     _order = 'sequence,name'

#     name = fields.Char(translation=True)
#     sequence = fields.Integer(default=10)
#     active = fields.Boolean(default=True)
#     fold = fields.Boolean()
#     state = fields.Selection(
#         [('draft', 'Draft'),
#          ('running', 'Borrowed'),
#          ('done', 'Returned'),
#          ('fined_lost', 'Fined or Lost'),
#          ('cancel', 'Canceled')],
#         default='draft',
#     )

