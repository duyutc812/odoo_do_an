from odoo import fields, models, api, _


class CardStage(models.Model):
    _name = 'lib.card.stage'
    _description = 'Card Stage'
    _order = 'sequence,name'

    name = fields.Char()
    sequence = fields.Integer(default=10)
    is_active = fields.Boolean(default=True)
    is_fold = fields.Boolean()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Confirm'),
        ('expire', 'Expire')
    ], default='draft', string="State")

    # @api.depends('state')
    # def _compute_name_card_stage(self):
    #     for card_stg in self:
    #         card_stg.name = dict(self._fields['state'].selection).get(self.state)
    #         print(dict(self._fields['state'].selection).get(self.state))


