from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CreateMetaBook(models.TransientModel):
    _name = 'create.meta.book'
    _description = 'Create Meta Book'

    book_id = fields.Many2one('lib.book', string='Mã sách')
    name_seq = fields.Char(string="Mã meta sách", default=lambda self: _('New'), readonly=True)
    description = fields.Text('Tình trạng', default='Tài liệu mới')
    state = fields.Selection([
        ('available', 'Có sẵn'),
        ('not_available', 'Không có sẵn')
    ], string='Trạng thái', default='available')
    quantity = fields.Integer('Số lượng')

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        book = self.env['lib.book'].sudo().search([('id', '=', self.env.context.get('active_id'))])
        defaults['book_id'] = book.id
        return defaults

    @api.multi
    def button_create(self):
        meta_book = self.env['lib.meta.books']
        if not self.quantity:
            raise ValidationError(_('Số lượng phải lớn hơn 0!'))
        for k in range(1, self.quantity+1):
            book_fields = list(meta_book._fields)
            book_vals = meta_book.default_get(book_fields)
            book_vals.update({'book_id': self.book_id.id,
                              'description': self.description,
                              'state': 'available'})
            meta_book.create(book_vals)
        self.book_id.message_post(_('%s đã cập nhật số lượng của sách \'%s\' là %s' % (str(self.create_uid.name), str(self.book_id.name), str(self.quantity))))
        return True


class CreateMetaMagazineNewspaper(models.TransientModel):
    _name = 'create.meta.mg.new'
    _description = 'Create Meta Magazine Newspaper'

    mgz_new_id = fields.Many2one('lib.magazine.newspaper', string='Tạp chí/Báo', track_visibility='always')
    name_seq = fields.Char(string="Mã meta tạp chí/báo", default=lambda self: _('New'), readonly=True)
    description = fields.Text('Tình trạng', default='Tài liệu mới')
    state = fields.Selection([
        ('available', 'Có sẵn'),
        ('not_available', 'Không có sẵn')
    ], string='Trạng thái', default='available')
    quantity = fields.Integer('Số lượng')

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        mg_new = self.env['lib.magazine.newspaper'].sudo().search([('id', '=', self.env.context.get('active_id'))])
        defaults['mgz_new_id'] = mg_new.id
        return defaults

    @api.multi
    def button_create(self):
        meta_mg_new = self.env['lib.meta.magazinenewspapers']
        if not self.quantity:
            raise ValidationError(_('Số lượng phải lớn hơn 0!'))
        for k in range(1, self.quantity + 1):
            mg_new_fields = list(meta_mg_new._fields)
            mg_new_vals = meta_mg_new.default_get(mg_new_fields)
            mg_new_vals.update({'mgz_new_id': self.mgz_new_id.id,
                                'description': self.description,
                                'state': 'available'})
            meta_mg_new.create(mg_new_vals)
        self.mgz_new_id.message_post(_('%s đã cập nhật số lượng của \'%s\' là %s' % (str(self.create_uid.name), str(self.mgz_new_id.name_get()[0][1]), str(self.quantity))))
        return True



