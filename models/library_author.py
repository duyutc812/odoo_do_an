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
    _name = 'library.author'
    _description = 'Author'
    _rec_name = 'pen_name'

    pen_name = fields.Char('Author', required=True)
    name = fields.Char('Name', required=True)
    author_image = fields.Binary('Cover', default=get_default_img())
    country_id = fields.Many2one('res.country', 'Nationality')
    born_date = fields.Date('Date of Birth')
    death_date = fields.Date('Date of Death')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', default='male')
    biography = fields.Text('Biography')
    note = fields.Html('Notes')

    _sql_constraints = [
        ('library_author_pen_name_uq',
         'UNIQUE (pen_name)',
         'The Pen-Name must be unique.')
    ]

    name_seq = fields.Char(string='Author ID', default=lambda self: _('New'), readonly=True)

    color = fields.Integer('Color Index')

    book_ids = fields.Many2many('library.book', 'library_author_library_book_rel',
                                'library_author_id', 'library_book_id', string='Books')

    count = fields.Integer(string="Count", compute='_get_book_count')
    active = fields.Boolean('Active', default=True)

    @api.multi
    def open_books_of_author2(self):
        return {
            'name': _('All book 2'),
            'domain': [('author_ids', '=', self.id)],
            'view_type': 'form',
            'res_model': 'library.book',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def _get_book_count(self):
        self.count = self.env['library.book'].search_count([('author_ids', '=', self.id)])
        # print(self.count)

    @api.model
    def create(self, vals):
        """Method to get name_seq"""
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('library.author.sequence') or _('New')
        result = super(Author, self).create(vals)

        return result


    @api.constrains('born_date')
    def _constrains_born_date(self):
        """Method to constrains born_date"""
        for rec in self:
            if rec.born_date and rec.born_date >= fields.Date.today():
                raise ValidationError("DOB is should be less then today date")


    @api.constrains('born_date', 'death_date')
    def _constrains_born_death(self):
        """Method to constrains born_date < death_date"""
        for rec in self:
            if rec.born_date and rec.death_date and rec.death_date <= rec.born_date:
                raise ValidationError('Death date is must be less then born date')

    @api.onchange('pen_name', 'name')
    def _onchange_pen_name_and_name_upper(self):
        """Method to set upper for name"""
        for rec in self:
            rec.pen_name = rec.pen_name.title() if rec.pen_name else ''
            rec.name = rec.name.title() if rec.name else ''

    def unlink(self):
        for rec in self:
            check_author_book = self.env['library.book'].search([
                ('author_ids', '=', rec.id)
            ])
            # print(check_author_book)
            if check_author_book:
                raise ValidationError('can not delete author!')
        return super(Author, self).unlink()
