from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning


class LibraryRack(models.Model):
    _name = 'lib.rack'
    _description = "Giá chứa tài liệu"

    name_seq = fields.Char('Mã giá')
    name = fields.Char('Tên giá chứa', required=True)
    is_active = fields.Boolean('Có hiệu lức', default='True')
    book_ids = fields.One2many('lib.book', 'rack', string='Sách')
    mg_new_ids = fields.One2many('lib.magazine.newspaper', 'rack', string='Tạp chí-báo')
    project_ids = fields.One2many('lib.document.project', 'rack', string='Đồ án-luận văn')

    _sql_constraints = [
        ('library_rack_name_seq_uniq',
         'unique (name_seq)',
         'Mã của các giá chứa tài liệu đã tồn tại!'),
        ('library_rack_name_uniq',
         'unique (name)',
         'Tên các giá chứa tài liệu đã tồn tại!'),
    ]

    def unlink(self):
        books = self.env['lib.book'].search([('rack', '=', self.id)])
        magazines = self.env['lib.magazine.newspaper'].search([('rack', '=', self.id)])
        projects = self.env['lib.document.project'].search([('rack', '=', self.id)])
        if books or magazines or projects:
            raise ValidationError(_('Bạn không thể xoá thông tin giá chứa do có các tài liệu phụ thuộc!'))
        return super(LibraryRack, self).unlink()


class Book(models.Model):
    _name = 'lib.book'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sách'

    name_seq = fields.Char(string="Mã sách", default=lambda self: _('New'), readonly=True, track_visibility='always')
    name = fields.Char(string="Tiêu đề", required=False, help='Tiêu đề sách')
    category = fields.Many2one('lib.category.book', 'Thể loại', required=True, track_visibility='always')
    publish_date = fields.Date('Ngày xuất bản', track_visibility='always')
    publisher_id = fields.Many2one('lib.publisher', string='Nhà xuất bản', track_visibility='always')
    author_ids = fields.Many2many('lib.author',
                                  string='Tác giả', track_visibility='always')
    translator_ids = fields.Many2many('lib.translator',
                                      string='Dịch giả', track_visibility='always')
    book_type = fields.Selection([
        ('paper', 'Bìa mềm'),
        ('hard', 'Bìa cứng'),
    ], string='Loại bìa', default='paper', track_visibility='always')
    image = fields.Binary('Ảnh')
    num_page = fields.Integer(string='Số trang', track_visibility='always')
    rack = fields.Many2one('lib.rack', string='Giá chứa', track_visibility='always')
    book_term = fields.Integer('Giới hạn mượn(ngày)')
    language_id = fields.Many2one('res.lang', 'Ngôn ngữ',
                                  default=lambda s: s.env['res.lang'].sudo().search([('code', '=', 'vi_VN')], limit=1),
                                  track_visibility='always')
    quantity = fields.Integer(string='Số lượng', compute='_compute_quantity_remaining', store=True)
    remaining = fields.Integer(string='Còn lại', compute='_compute_quantity_remaining', store=True)
    state = fields.Selection([
        ('available', 'Có sẵn'),
        ('not_available', 'Không có sẵn')
    ], string='Trạng thái', compute='_compute_quantity_remaining', store=True)
    currency_id = fields.Many2one('res.currency', 'Tiền tệ',
                                  default=lambda s: s.env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1)
                                  )
    price = fields.Monetary('Giá tiền', 'currency_id', track_visibility='always')
    is_active = fields.Boolean('Có hiệu lực', default=True)
    meta_book_ids = fields.One2many(
        'lib.meta.books',
        'book_id',
    )

    # def test(self):
    #     print(self.message_main_attachment_id)

    @api.constrains('price', 'num_page', 'book_term')
    def _constrains_price(self):
        for book in self:
            if book.price <= 0:
                raise ValidationError(_('Giá sách phải lớn hơn 0!'))
            if book.num_page <= 0:
                raise ValidationError(_('Số trang sách phải lớn hơn 0!'))
            if book.book_term <= 0:
                raise ValidationError(_('Giới hạn mượn sách phải lớn hơn 0!'))

    @api.depends('meta_book_ids')
    def _compute_quantity_remaining(self):
        for book in self:
            book.quantity = len(book.meta_book_ids)
            book.remaining = len(
                book.meta_book_ids.filtered(
                    lambda a: a.state == 'available'
                )
            )
            book.state = 'not_available'
            if book.remaining > 0:
                book.state = 'available'

    @api.multi
    def name_get(self):
        res = []
        for book in self:
            res.append((book.id, '%s - %s' % (book.name_seq, book.name)))
        return res

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('lib.book.sequence') or _('New')
        result = super(Book, self).create(vals)
        return result

    @api.onchange('name')
    def _onchange_book_name(self):
        self.name = self.name.title() if self.name else ''

    def unlink(self):
        for book in self:
            if len(book.meta_book_ids):
                raise ValidationError(_('Bạn không thể xoá sách khi meta sách còn tồn tại!'))
        return super(Book, self).unlink()


class MetaBook(models.Model):
    _name = 'lib.meta.books'
    _description = 'Meta sách'

    name_seq = fields.Char(string="Mã Meta sách", default=lambda self: _('New'), readonly=True)
    book_id = fields.Many2one('lib.book', string='Sách')
    description = fields.Text('Tình trạng', default=_('Tài liệu mới'))
    sequence = fields.Integer()
    state = fields.Selection([
        ('available', 'Có sẵn'),
        ('not_available', 'Không có sẵn')
    ], string='Trạng thái', default='available')
    checkout = fields.Char('Phiếu mượn')
    is_lost = fields.Boolean('Đã mất', default=False)
    is_active = fields.Boolean('Có hiệu lực', default=True)

    @api.onchange('is_lost')
    def onchange_is_lost(self):
        for meta_bk in self:
            if meta_bk.is_lost:
                meta_bk.state = 'not_available'

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s' % (rec.name_seq)))
        return res

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('lib.meta.books.sequence') or _('New')
        result = super(MetaBook, self).create(vals)
        return result

    def unlink(self):
        chk_lib = self.env['lib.checkout.at.lib']
        chk_bh = self.env['lib.checkout.back.home']
        for book in self:
            if book.checkout or chk_lib.sudo().search([('meta_book_id', '=', book.id)]) or chk_bh.search([('meta_book_id', '=', book.id)]):
                raise ValidationError(_('Bạn không thể xoá meta sách: %s khi meta sách đang được mượn!' % (book.name_seq)))
            return super(MetaBook, self).unlink()



