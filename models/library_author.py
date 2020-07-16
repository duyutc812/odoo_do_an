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
    _description = 'Author'
    _rec_name = 'pen_name'

    name_seq = fields.Char(string='Author ID', default=lambda self: _('New'), readonly=True)
    pen_name = fields.Char('Author', required=True)
    name = fields.Char('Name', required=True)
    author_image = fields.Binary('Cover', default=get_default_img())
    born_date = fields.Date('Date of Birth')
    death_date = fields.Date('Date of Death')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', default='male')
    biography = fields.Text('Biography')
    country_id = fields.Many2one('res.country', 'Nationality')
    is_active = fields.Boolean('Active', default=True)
    count = fields.Integer(string="Count", compute='_get_book_count')
    book_ids = fields.Many2many('lib.book', 'lib_author_lib_book_rel',
                                'lib_author_id', 'lib_book_id', string='Books')

    _sql_constraints = [
        ('lib_author_pen_name_uq',
         'UNIQUE (pen_name)',
         'The Pen-Name must be unique.'),
        ('lib_author_born_date_chk',
         'CHECK (born_date < current_date)',
         'DOB is should be less then today date'),
        ('lib_author_born_date_death_date_chk',
         'CHECK (born_date < death_date)',
         'Death date is must be great then born date'),
        ('lib_author_death_date_chk',
         'CHECK (death_date <= current_date)',
         'Death date is must be less then current date'),
    ]

    @api.multi
    def open_books_of_author2(self):
        return {
            'name': _('All book 2'),
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
                raise ValidationError(_('can not delete author!'))
        return super(Author, self).unlink()


class LibraryTranslator(models.Model):
    _name = 'lib.translator'
    _description = 'Library Translator'

    name = fields.Char('Name', required=True)
    country_id = fields.Many2one('res.country', 'Nationality')
    born_date = fields.Date('Date of Birth')
    death_date = fields.Date('Date of Death')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', default='male')
    is_active = fields.Boolean('Active', default=True)
    book_ids = fields.Many2many('lib.book', 'lib_book_lib_translator_rel',
                                'lib_translator_id', 'lib_book_id', string='All book')

    @api.onchange('name')
    def _onchange_pen_name_and_name_upper(self):
        """Method to set upper for name"""
        self.name = self.name.title() if self.name else ''
