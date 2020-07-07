from odoo import api, fields, models, _


class CategoryBook(models.Model):
    _name = 'lib.category.book'
    _description = 'Category Book'
    # _parent_store = True

    name = fields.Char(required=True)

    # parent_id = fields.Many2one('lib.category', string='Parent Category',
    #                             ondelete='restrict')
    #
    # parent_path = fields.Char(index=True)
    #
    # child_ids = fields.One2many('lib.category', 'parent_id',
    #                             string='Subcategories')

    # book_ids = fields.One2many('lib.book', 'category')


class CategoryMagazine(models.Model):
    _name = 'lib.category.magazine'
    _description = 'Category Magazine'

    name = fields.Char('Name')


class CategoryNewspaper(models.Model):
    _name = 'lib.category.newspaper'
    _description = 'Category Newspaper'

    name = fields.Char('Name')



