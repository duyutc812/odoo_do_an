from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Major(models.Model):
    _name = 'lib.student.major'
    _description = 'Chuyên ngành'

    name = fields.Char('Tên chuyên ngành')

    @api.constrains('name')
    def _constraint_name(self):
        if self.search([('name', 'ilike', self.name), ('id', '!=', self.id)]):
            raise ValidationError(_('Tên chuyên ngành đã tồn tại!'))

    @api.onchange('name')
    def _onchange_name(self):
        self.name = self.name.title() if self.name else ''

    def unlink(self):
        for rec in self:
            students = self.env['lib.student'].search([
                ('major_id', '=', rec.id)
            ])
            if students:
                raise ValidationError(_('Không thể xoá chuyên ngành khi thông tin của sinh '
                                        'viên thuộc chuyên ngành còn tồn tại!'))
        return super(Major, self).unlink()