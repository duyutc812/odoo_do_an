from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Book(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _rec_name = 'book_name'

    book_name = fields.Char(string="Title", required=False, help='Book cover title')
    book_type = fields.Selection([
        ('paper', 'Paperback'),
        ('hard', 'Hardcover'),
    ], string='Type', default='paper')
    notes = fields.Text('Internal Notes',
                        default='User have to pay 50% - 70% of the book price if they lose the book')
    isbn = fields.Char('ISBN')
    currency_id = fields.Many2one('res.currency', default=23)
    price = fields.Monetary('Price', 'currency_id')
    language = fields.Selection([
        ('vn', 'Vietnamese'),
        ('en', 'English'),
    ], string='Language', default="vn")

    category = fields.Many2one('library.category', 'Category')
    num_page = fields.Integer(string='Num Page')

    """Date fields"""
    published_date = fields.Date('Published Date')

    """Relational Fields"""
    publisher_id = fields.Many2one('library.publisher', string='Publisher')
    author_ids = fields.Many2many('library.author',
                                  string='Author')

    """Other fields"""
    active = fields.Boolean('Active?', default=True)
    image = fields.Binary('Cover')

    book_ids = fields.One2many('meta.books', 'book_id')
    color = fields.Integer('Color')

    """name sequence"""
    name_seq = fields.Char(string="Book ID", default=lambda self: _('New'), readonly=True)

    quantity = fields.Integer(string='Quantity', compute='_get_count_book_ids', store=True)
    actually = fields.Integer(string='Actually', compute='_get_actually_meta_book', store=True)

    availability = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Availability', compute='_set_availability', store=True)

    @api.depends('book_ids')
    def _get_count_book_ids(self):
        for r in self:
            r.quantity = len(r.book_ids)

    @api.depends('book_ids')
    def _get_actually_meta_book(self):
        for r in self:
            r.actually = r.book_ids.search_count([
                ('book_id', '=', r.id),
                ('is_available', '=', 'available')
            ])

    @api.depends('actually')
    def _set_availability(self):
        for r in self:
            if r.actually != 0:
                r.availability = 'available'
            else:
                r.availability = 'not_available'
        return True

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s - %s' % (rec.name_seq, rec.book_name)))
        return res

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('library.book.sequence') or _('New')
        result = super(Book, self).create(vals)
        return result

    @api.onchange('book_name')
    def _onchange_book_name(self):
        for rec in self:
            rec.book_name = rec.book_name.title() if rec.book_name else ''

    def unlink(self):
        for rec in self:
            check_checkout_book = self.env['library.checkout'].search([
                ('borrow_book', '=', rec.id)
            ])
            # print(check_checkout_book)
            if check_checkout_book:
                raise ValidationError('Can not delete book!')
        return super(Book, self).unlink()


class MetaBook(models.Model):
    _name = 'meta.books'
    _description = 'Meta book'

    book_id = fields.Many2one('library.book', string='Book')
    name_seq = fields.Char(string="Meta Book ID", default=lambda self: _('New'), readonly=True)

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s - %s' % (rec.name_seq, rec.book_id.book_name)))
        return res

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('library.meta.books.sequence') or _('New')
        result = super(MetaBook, self).create(vals)
        return result

    status = fields.Text('Status')
    is_available = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Availability', default='available')


class Magazine(models.Model):
    _name = 'library.magazine'
    _description = 'Magazine and newspaper'

    type = fields.Selection([
        ('magazine', 'Magazine'),
        ('newspaper', 'Newspaper')
    ], string='Type', default='newspaper')
    image = fields.Binary('Cover')
    category_mgz = fields.Many2one('categories.magazine', string='Category Magazine')
    category_new = fields.Many2one('categories.newspaper', string='Category Newspaper')
    num_magazine = fields.Integer(string="No.")
    publish_date = fields.Date(string='Publish Date')

    mgz_new_ids = fields.One2many('meta.magazinenewspaper', 'mgz_new_id')
    quantity = fields.Integer(string='Quantity', compute='_get_count_mgz_new', store=True)
    actually = fields.Integer(string='Actually', compute='_get_actually_mgz_new', store=True)

    availability = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Availability', compute='_set_availability', store=True)

    @api.depends('mgz_new_ids')
    def _get_count_mgz_new(self):
        for r in self:
            r.quantity = len(r.mgz_new_ids)

    @api.depends('mgz_new_ids')
    def _get_actually_mgz_new(self):
        for r in self:
            r.actually = r.mgz_new_ids.search_count([
                ('mgz_new_id', '=', r.id),
                ('is_available', '=', 'available')
            ])

    @api.depends('actually')
    def _set_availability(self):
        for r in self:
            if r.actually != 0:
                r.availability = 'available'
            else:
                r.availability = 'not_available'
        return True

    active = fields.Boolean('Active?', default=True)

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, 'Magazine %s - No.%s'
                        % (rec.category_mgz.name if rec.category_mgz else rec.category_new.name, rec.num_magazine)))
        return res


class MetaMagazineNewspaper(models.Model):
    _name = 'meta.magazinenewspaper'
    _description = 'Meta Magazine Newspaper'

    mgz_new_id = fields.Many2one('library.magazine', string='Magazine/Newspaper')
    name_seq = fields.Char(string="Meta Book ID", default=lambda self: _('New'), readonly=True)

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s - %s' % (rec.name_seq, rec.mgz_new_id)))
        return res

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('library.meta.magazine.newspaper.sequence') or _('New')
        result = super(MetaMagazineNewspaper, self).create(vals)
        return result

    status = fields.Text('Status')
    is_available = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Availability', default='available')


class Project(models.Model):
    _name = 'document.project'
    _description = 'Document - Project'

    name = fields.Char('Name Project', required=True)
    major = fields.Many2one('student.major', string='Major', requied=True)
    student_id = fields.Many2one('library.student', string='Student ID')
    student_name = fields.Char('Name Student', related='student_id.name', store=True)
    course = fields.Integer('Course', related='student_id.course', store=True)
    publish_date = fields.Date('Publish Date')
    teacher_name = fields.Many2one('library.teacher')

    availability = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Availability', default='available')

    @api.onchange('major')
    def _onchange_student_major(self):
        for r in self:
            r.student_id = ''
            return {'domain': {'student_id': [('major', '=', r.major.id)]}}


class CategoriesMagazine(models.Model):
    _name = 'categories.magazine'
    _description = 'Categories Magazine'

    name = fields.Char('Name')


class CategoriesNewspaper(models.Model):
    _name = 'categories.newspaper'
    _description = 'Categories Newspaper'

    name = fields.Char('Name')








