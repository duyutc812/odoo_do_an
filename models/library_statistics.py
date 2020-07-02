from odoo import api, fields, models, _


class LibraryStatistics(models.Model):
    _name = 'library.statistics'
    _description = 'Library Statistics'

    create_date = fields.Datetime(string="Create Date", default=fields.Datetime.now())
    num_book = fields.Integer('Number Book In Lib', compute='_compute_statistics')
    num_meta_book = fields.Integer('Number Meta Book In Lib', compute='_compute_statistics')
    num_meta_book_lost = fields.Integer('Number Meta Book Lost In Lib', compute='_compute_statistics')

    @api.multi
    def _compute_statistics(self):
        Meta_books = self.env['meta.books']
        for lib_st in self:
            lib_st.num_book = self.env['library.book'].sudo().search_count([])
            lib_st.num_meta_book = Meta_books.sudo().search_count([])
            lib_st.num_meta_book_lost = Meta_books.sudo().search_count([('is_lost', '=', True)])
