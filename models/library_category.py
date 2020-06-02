from odoo import api, fields, models, _


class Category(models.Model):
    _name = 'library.category'
    _description = 'Category'
    # _parent_store = True
    _rec_name = 'name'

    name = fields.Char(required=True)

    # parent_id = fields.Many2one('library.category', string='Parent Category',
    #                             ondelete='restrict')
    #
    # parent_path = fields.Char(index=True)
    #
    # child_ids = fields.One2many('library.category', 'parent_id',
    #                             string='Subcategories')

    # book_ids = fields.One2many('library.book', 'category')


class CategoriesMagazine(models.Model):
    _name = 'categories.magazine'
    _description = 'Categories Magazine'

    name = fields.Char('Name')


class CategoriesNewspaper(models.Model):
    _name = 'categories.newspaper'
    _description = 'Categories Newspaper'

    name = fields.Char('Name')



