import base64
from odoo import modules
from odoo import api, fields, models, _
from odoo.exceptions import Warning, ValidationError

"""Method to get default_image"""
def get_default_img():
    with open(modules.get_module_resource('do_an_tn', 'static/', 'default_image.png'),
              'rb') as f:
        return base64.b64encode(f.read())


class Author(models.Model):
    _name = 'lib.author'
    _description = 'Tác giả'
    _rec_name = 'pen_name'

    name_seq = fields.Char(string='Mã TG', default=lambda self: _('New'), readonly=True)
    pen_name = fields.Char('Bút danh', required=True)
    name = fields.Char('Tên thật', required=True)
    author_image = fields.Binary('Ảnh', default=get_default_img())
    born_date = fields.Date('Ngày sinh')
    death_date = fields.Date('Ngày mất')
    gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
    ], string='Giới tính', default='male')
    biography = fields.Text('Tiểu sử')
    country_id = fields.Many2one('res.country', 'Quốc tịch', default=lambda s: s.env['res.country'].search([('code', '=', 'VN')], limit=1))
    is_active = fields.Boolean('Có hiệu lực', default=True)
    count = fields.Integer(string="Tổng số sách", compute='_get_book_count')
    book_ids = fields.Many2many('lib.book', 'lib_author_lib_book_rel',
                                'lib_author_id', 'lib_book_id', string='Tất cả sách')

    _sql_constraints = [
        ('lib_author_pen_name_uq',
         'UNIQUE (pen_name)',
         'Bút danh đã tồn tại!'),
        ('lib_author_born_date_chk',
         'CHECK (born_date < current_date)',
         'Ngày sinh phải nhỏ hơn ngày hiện tại!'),
        ('lib_author_born_date_death_date_chk',
         'CHECK (born_date < death_date)',
         'Ngày sinh phải nhỏ hơn ngày mất!'),
        ('lib_author_death_date_chk',
         'CHECK (death_date <= current_date)',
         'Ngày mất phải nhỏ hơn hoặc bằng ngày hiện tại!'),
    ]

    @api.multi
    def open_books_of_author2(self):
        return {
            'name': _('Tất cả sách'),
            'domain': [('author_ids', '=', self.id)],
            'view_type': 'form',
            'res_model': 'lib.book',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def _get_book_count(self):
        for author in self:
            author.count = self.env['lib.book'].search_count([('author_ids', '=', author.id)])
        # print(self.count)

    @api.model
    def create(self, vals):
        """Method to get name_seq"""
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('lib.author.sequence') or _('New')
        result = super(Author, self).create(vals)

        return result

    @api.onchange('pen_name', 'name')
    def _onchange_pen_name_and_name_upper(self):
        """Method to set upper for name"""
        self.pen_name = self.pen_name.title() if self.pen_name else ''
        self.name = self.name.title() if self.name else ''

    @api.multi
    def toggle_active(self):
        for author in self:
            if author.is_active:
                author.is_active = False
            else:
                author.is_active = True

    def unlink(self):
        for rec in self:
            check_author_book = self.env['lib.book'].search([
                ('author_ids', '=', rec.id)
            ])
            # print(check_author_book)
            if check_author_book:
                raise ValidationError(_('Không thể xoá tác giả khi sách của tác giả đang tồn tại!'))
        return super(Author, self).unlink()


class LibraryTranslator(models.Model):
    _name = 'lib.translator'
    _description = 'Dịch giả'

    name = fields.Char('Họ tên', required=True)
    country_id = fields.Many2one('res.country', 'Quốc tịch', default=lambda s: s.env['res.country'].search([('code', '=', 'VN')], limit=1))
    born_date = fields.Date('Ngày sinh')
    death_date = fields.Date('Ngày mất')
    gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
    ], string='Giới tính', default='male')
    is_active = fields.Boolean('Có hiệu lực', default=True)
    book_ids = fields.Many2many('lib.book', 'lib_book_lib_translator_rel',
                                'lib_translator_id', 'lib_book_id', string='Tất cả sách')

    @api.onchange('name')
    def _onchange_pen_name_and_name_upper(self):
        """Method to set upper for name"""
        self.name = self.name.title() if self.name else ''

    def unlink(self):
        for rec in self:
            check_translator_book = self.env['lib.book'].search([
                ('translator_ids', '=', rec.id)
            ])
            # print(check_author_book)
            if check_translator_book:
                raise ValidationError(_('Không thể xoá dịch giả khi sách của dịch giả đang tồn tại!'))
        return super(LibraryTranslator, self).unlink()

    _sql_constraints = [
        ('lib_translator_born_date_chk',
         'CHECK (born_date < current_date)',
         'Ngày sinh phải nhỏ hơn ngày hiện tại!'),
        ('lib_translator_born_date_death_date_chk',
         'CHECK (born_date < death_date)',
         'Ngày sinh phải nhỏ hơn ngày mất!'),
        ('lib_translator_death_date_chk',
         'CHECK (death_date <= current_date)',
         'Ngày mất phải nhỏ hơn hoặc bằng ngày hiện tại!'),
    ]

