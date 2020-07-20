from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CardStage(models.Model):
    _name = 'lib.card.stage'
    _description = 'Giai đoạn thẻ thư viện'
    _order = 'sequence,name'

    name = fields.Char('Tên giai đoạn', required=True)
    sequence = fields.Integer(default=10, string="Thứ tự")
    is_active = fields.Boolean(default=True, string="Có hiệu lực")
    is_fold = fields.Boolean('Gập?')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('running', 'Đã xác nhận'),
        ('expire', 'Hết hạn')
    ], default='draft', string="Giai đoạn")

    @api.constrains('name')
    def _constraint_name(self):
        if self.search([('name', 'ilike', self.name), ('id', '!=', self.id)]):
            raise ValidationError(_('Tên giai đoạn thẻ mượn đã tồn tại!'))

    @api.onchange('name')
    def _onchange_name(self):
        self.name = self.name.title() if self.name else ''

    def unlink(self):
        for rec in self:
            cards = self.env['lib.card'].search([
                ('stage_id', '=', rec.id)
            ], limit=1)
            if cards:
                raise ValidationError(_('Không thể xoá giai đoạn thẻ mượn khi thông tin của thẻ mượn thư viện '
                                        'thuộc giai đoạn này còn tồn tại!'))
        return super(CardStage, self).unlink()

    # @api.depends('state')
    # def _compute_name_card_stage(self):
    #     for card_stg in self:
    #         card_stg.name = dict(self._fields['state'].selection).get(self.state)
    #         print(dict(self._fields['state'].selection).get(self.state))


