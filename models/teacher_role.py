from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TeacherRole(models.Model):
    _name = 'lib.teacher.role'
    _description = 'Chức vụ giảng viên'

    name = fields.Char('Chức vụ giảng viên')

    @api.constrains('name')
    def _constraint_name(self):
        if self.search([('name', 'ilike', self.name), ('id', '!=', self.id)]):
            raise ValidationError(_('Tên chức vụ của giảng viên đã tồn tại!'))

    @api.onchange('name')
    def _onchange_name(self):
        self.name = self.name.title() if self.name else ''

    def unlink(self):
        for rec in self:
            teacher = self.env['lib.teacher'].search([
                ('role', '=', rec.id)
            ])
            if teacher:
                raise ValidationError(_('Không thể xoá chức vụ giảng viên khi thông tin của giảng '
                                        'viên thuộc chức vụ này còn tồn tại!'))
        return super(TeacherRole, self).unlink()