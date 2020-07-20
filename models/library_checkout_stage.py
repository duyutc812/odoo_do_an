from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CheckoutStage(models.Model):
    _name = 'lib.checkout.stage'
    _description = 'Giai đoạn phiếu mượn'
    _order = 'sequence,name'

    name = fields.Char(required=True, string='Tên giai đoạn')
    sequence = fields.Integer(default=10, string='Thứ tự')
    is_active = fields.Boolean(default=True, string='Có hiệu lực')
    is_fold = fields.Boolean('Gập?')
    state = fields.Selection(
        [('draft', 'Nháp'),
         ('running', 'Đã mượn'),
         ('done', 'Đã trả'),
         ('fined', 'Bị phạt'),
         ('lost', 'Mất tài liệu')],
        default='draft', string="Giai đoạn"
    )

    @api.constrains('name')
    def _constraint_name(self):
        if self.search([('name', 'ilike', self.name), ('id', '!=', self.id)]):
            raise ValidationError(_('Tên giai đoạn phiếu mượn đã tồn tại!'))

    @api.onchange('name')
    def _onchange_name(self):
        self.name = self.name.title() if self.name else ''

    def unlink(self):
        for rec in self:
            chk_at_libs = self.env['lib.checkout.at.lib'].search([('stage_id', '=', rec.id)], limit=1)
            chk_back_homes = self.env['lib.checkout.back.home'].search([('stage_id', '=', rec.id)], limit=1)
            if chk_at_libs or chk_back_homes:
                raise ValidationError(_('Không thể xoá giai đoạn phiếu mượn khi thông tin của phiếu mượn thư viện '
                                        'thuộc giai đoạn này còn tồn tại!'))
        return super(CheckoutStage, self).unlink()


