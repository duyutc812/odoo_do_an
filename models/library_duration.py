from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LibraryDuration(models.Model):
    _name = 'lib.duration'
    _description = 'Thời hạn'

    name = fields.Char('Tên Thời hạn', readonly=True, compute='_compute_name', store=True)
    duration = fields.Integer('Thời hạn(tháng)', required=True)
    member_type = fields.Selection([
        ('student', 'Sinh viên'),
        ('teacher', 'Giảng viên'),
    ], string='Loại độc giả', default='student')
    book_limit = fields.Integer('Giới hạn sách', required=True)
    syllabus_limit = fields.Integer('Giới hạn giáo trình', required=True)

    currency_id = fields.Many2one('res.currency', 'Tiền tệ',
                                  default=lambda s: s.env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1))
    price = fields.Monetary('Giá', 'currency_id')

    @api.depends('duration', 'member_type')
    def _compute_name(self):
        for lib_dur in self:
            lib_member_type = dict(self._fields['member_type'].selection).get(self.member_type)
            lib_dur.name = str(lib_dur.duration) + (' tháng' if lib_dur.duration > 1 else 'tháng') \
                           + '(' + str(lib_member_type) + ')'

    @api.constrains('duration')
    def _constrains_duration(self):
        if self.duration <= 0:
            raise ValidationError(_('Thời hạn phải lớn hơn 0!'))

    _sql_constraints = [
        ('duration_member_type_uniq',
         'unique (duration, member_type)',
         'Thời hạn cho từng loại độc giả đã tồn tại!'),
    ]

    def unlink(self):
        for rec in self:
            check_duration_card = self.env['lib.card'].search([
                ('duration_id', '=', rec.id)
            ])
            # print(check_author_book)
            if check_duration_card:
                raise ValidationError(_('Không thể xoá thông tin thời hạn này do có thẻ đang sử dụng nó!'))
        return super(LibraryDuration, self).unlink()

