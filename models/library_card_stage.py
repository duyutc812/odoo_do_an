from odoo import fields, models


class CardStage(models.Model):
    _name = 'lib.card.stage'
    _description = 'Card Stage'
    _order = 'sequence,name'

    name = fields.Char(translation=True)
    sequence = fields.Integer(default=10)
    is_active = fields.Boolean(default=True)
    is_fold = fields.Boolean()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Confirm'),
        ('expire', 'Expire')
    ], default='draft', string="State")