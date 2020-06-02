from odoo import fields, models


class CardStage(models.Model):
    _name = 'library.card.stage'
    _description = 'Card Stage'
    _order = 'sequence,name'

    name = fields.Char(translation=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    fold = fields.Boolean()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Confirm'),
        ('expire', 'Expire')
    ], default='draft', string="State")