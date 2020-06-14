from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning


class LibraryRack(models.Model):
    _name = 'library.rack'
    _description = "Library Rack"

    name = fields.Char('Name', required=True,
                       help="it will be show the position of book")
    code = fields.Char('Code')
    active = fields.Boolean('Active', default='True')
    book_ids = fields.One2many('library.book', 'rack', 'All Book')


class Book(models.Model):
    _name = 'library.book'
    _description = 'Library Book'

    name = fields.Char(string="Title", required=False, help='Book cover title')
    book_type = fields.Selection([
        ('paper', 'Paperback'),
        ('hard', 'Hardcover'),
    ], string='Type', default='paper')
    notes = fields.Text('Notes',
                        default='User have to pay 50% - 70% of the book price if they lose the book')
    isbn = fields.Char('ISBN')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda s: s.env['res.currency'].search([], limit=1))
    price = fields.Monetary('Price', 'currency_id')
    language = fields.Many2one('res.lang', 'Language',
                               default=lambda s: s.env['res.lang'].search([], limit=1))
    category = fields.Many2one('library.category', 'Category')
    num_page = fields.Integer(string='Num Page')
    rack = fields.Many2one('library.rack', string='Library Rack')

    """Date fields"""
    published_date = fields.Date('Published Date')

    """Relational Fields"""
    publisher_id = fields.Many2one('library.publisher', string='Publisher')
    author_ids = fields.Many2many('library.author',
                                  string='Author')
    translator_ids = fields.Many2many('library.translator',
                                      string='Translator')

    """Other fields"""
    active = fields.Boolean('Active?', default=True)
    image = fields.Binary('Cover')

    color = fields.Integer('Color')

    """name sequence"""
    name_seq = fields.Char(string="Book ID", default=lambda self: _('New'), readonly=True)

    quantity = fields.Integer(string='Quantity', compute='_compute_quantity_remaining', store=True)
    remaining = fields.Integer(string='Remaining', compute='_compute_quantity_remaining', store=True)

    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', compute='_compute_state_book', store=True)

    meta_book_ids = fields.One2many(
        'meta.books',
        'book_id',
    )

    @api.depends('meta_book_ids')
    def _compute_quantity_remaining(self):
        for book in self:
            book.quantity = len(book.meta_book_ids)
            remaining = len(
                book.meta_book_ids.filtered(
                    lambda a: a.state == 'available'
                )
            )
            book.remaining = remaining

    @api.depends('remaining')
    def _compute_state_book(self):
        for book in self:
            book.state = 'available' if book.remaining > 0 else 'not_available'

    @api.multi
    def name_get(self):
        res = []
        for book in self:
            res.append((book.id, '%s - %s' % (book.name_seq, book.name)))
        return res

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('library.book.sequence') or _('New')
        result = super(Book, self).create(vals)
        return result

    @api.onchange('name')
    def _onchange_book_name(self):
        for book in self:
            book.name = book.name.title() if book.name else ''

    def unlink(self):
        for book in self:
            if len(book.meta_book_ids) > 0:
                raise ValidationError('You can not delete book!')
        return super(Book, self).unlink()






