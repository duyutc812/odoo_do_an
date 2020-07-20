from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CategoryBook(models.Model):
    _name = 'lib.category.book'
    _description = 'Thể loại sách'
    # _parent_store = True

    name = fields.Char(required=True, string="Thể loại sách")

    # parent_id = fields.Many2one('lib.category', string='Parent Category',
    #                             ondelete='restrict')
    #
    # parent_path = fields.Char(index=True)
    #
    # child_ids = fields.One2many('lib.category', 'parent_id',
    #                             string='Subcategories')

    # book_ids = fields.One2many('lib.book', 'category')

    @api.constrains('name')
    def _constraint_name(self):
        if self.search([('name', 'ilike', self.name), ('id', '!=', self.id)]):
            raise ValidationError(_('Tên thể loại sách đã tồn tại!'))

    @api.onchange('name')
    def _onchange_name(self):
        self.name = self.name.title() if self.name else ''

    def unlink(self):
        for rec in self:
            books = self.env['lib.book'].search([
                ('category', '=', rec.id)
            ])
            if books:
                raise ValidationError(_('Không thể xoá thể loại sách khi thông tin của sách '
                                        'viên thuộc thể loại này còn tồn tại!'))
        return super(CategoryBook, self).unlink()


class CategoryMagazine(models.Model):
    _name = 'lib.category.magazine'
    _description = 'Thể loại tạp chí'

    name = fields.Char('Thể loại tạp chí', required=True)

    @api.constrains('name')
    def _constraint_name(self):
        if self.search([('name', 'ilike', self.name), ('id', '!=', self.id)]):
            raise ValidationError(_('Tên thể loại tạp chí đã tồn tại!'))

    @api.onchange('name')
    def _onchange_name(self):
        self.name = self.name.title() if self.name else ''

    def unlink(self):
        for rec in self:
            books = self.env['lib.magazine.newspaper'].search([
                ('category_mgz_id', '=', rec.id)
            ])
            if books:
                raise ValidationError(_('Không thể xoá thể loại tạp chí khi thông tin của tạp chí '
                                        'thuộc thể loại này còn tồn tại!'))
        return super(CategoryMagazine, self).unlink()


class CategoryNewspaper(models.Model):
    _name = 'lib.category.newspaper'
    _description = 'Thể loại báo'

    name = fields.Char('Thể loại báo', required=True)

    @api.constrains('name')
    def _constraint_name(self):
        if self.search([('name', 'ilike', self.name), ('id', '!=', self.id)]):
            raise ValidationError(_('Tên thể loại báo này đã tồn tại!'))

    @api.onchange('name')
    def _onchange_name(self):
        self.name = self.name.title() if self.name else ''

    def unlink(self):
        for rec in self:
            books = self.env['lib.magazine.newspaper'].search([
                ('category_new_id', '=', rec.id)
            ])
            if books:
                raise ValidationError(_('Không thể xoá thể loại báo khi thông tin của báo '
                                        'thuộc thể loại này còn tồn tại!'))
        return super(CategoryNewspaper, self).unlink()


