from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning


class LibraryRack(models.Model):
    _name = 'lib.rack'
    _description = "Library Rack"

    name_seq = fields.Char('Code')
    name = fields.Char('Name', required=True,
                       help="it will be show the position of book")
    is_active = fields.Boolean('Active', default='True')
    book_ids = fields.One2many('lib.book', 'rack', string='All Book')
    mg_new_ids = fields.One2many('lib.magazine.newspaper', 'rack', string='Magazine/Newspaper')
    project_ids = fields.One2many('lib.document.project', 'rack', string='All Project')


class Book(models.Model):
    _name = 'lib.book'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Library Book'

    name_seq = fields.Char(string="Book ID", default=lambda self: _('New'), readonly=True, track_visibility='always')
    name = fields.Char(string="Title", required=False, help='Book cover title')
    category = fields.Many2one('lib.category.book', 'Category', required=True, track_visibility='always')
    publish_date = fields.Date('Publish Date', track_visibility='always')
    publisher_id = fields.Many2one('lib.publisher', string='Publisher', track_visibility='always')
    author_ids = fields.Many2many('lib.author',
                                  string='Author', track_visibility='always')
    translator_ids = fields.Many2many('lib.translator',
                                      string='Translator', track_visibility='always')
    book_type = fields.Selection([
        ('paper', 'Paperback'),
        ('hard', 'Hardcover'),
    ], string='Type', default='paper', track_visibility='always')
    image = fields.Binary('Cover')
    num_page = fields.Integer(string='Num Page', track_visibility='always')
    rack = fields.Many2one('lib.rack', string='Library Rack', track_visibility='always')
    book_term = fields.Integer('Book Term (Days)')
    language_id = fields.Many2one('res.lang', 'Language',
                                  default=lambda s: s.env['res.lang'].sudo().search([('code', '=', 'vi_VN')], limit=1),
                                  track_visibility='always')
    quantity = fields.Integer(string='Quantity', compute='_compute_quantity_remaining', store=True)
    remaining = fields.Integer(string='Remaining', compute='_compute_quantity_remaining', store=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', compute='_compute_quantity_remaining', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda s: s.env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1)
                                  )
    price = fields.Monetary('Price', 'currency_id', track_visibility='always')
    is_active = fields.Boolean('Active?', default=True)
    meta_book_ids = fields.One2many(
        'lib.meta.books',
        'book_id',
    )

    def test(self):
        print(self.message_main_attachment_id)

    @api.constrains('price', 'num_page', 'book_term')
    def _constrains_price(self):
        for book in self:
            if book.price <= 0:
                raise ValidationError(_('The price must be greater than 0!'))
            if book.num_page <= 0:
                raise ValidationError(_('The num page must be greater than 0!'))
            if book.book_term <= 0:
                raise ValidationError(_('The book term must be greater than 0!'))

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
                raise ValidationError(_('You can not delete book!'))
        return super(Book, self).unlink()


class MetaBook(models.Model):
    _name = 'lib.meta.books'
    _description = 'Meta book'

    name_seq = fields.Char(string="Meta Book ID", default=lambda self: _('New'), readonly=True)
    book_id = fields.Many2one('lib.book', string='Book')
    description = fields.Text('Description', default=_('Tài liệu mới'))
    sequence = fields.Integer()
    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', default='available')
    checkout = fields.Char()
    is_lost = fields.Boolean('Lost', default=False)
    is_active = fields.Boolean('Active', default=True)

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
                raise ValidationError(_('You cannot delete record %s!' % (book.name_seq)))
            return super(MetaBook, self).unlink()



