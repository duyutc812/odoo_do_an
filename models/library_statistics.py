from odoo import api, fields, models, _


class LibraryStatistics(models.Model):
    _name = 'lib.statistics'
    _description = 'Library Statistics'

    create_date = fields.Datetime(string="Create Date", default=fields.Datetime.now())
    book = fields.Integer('Number Book In Lib', compute='_compute_statistics')
    meta_book = fields.Integer('Number Meta Book In Lib', compute='_compute_statistics')
    meta_book_lost = fields.Integer('Number Meta Book Lost In Lib', compute='_compute_statistics')

    mgz = fields.Integer('Magazine-Newspaper', compute='_compute_statistics')
    meta_mgz = fields.Integer('Meta Magazine-Newspaper', compute='_compute_statistics')
    meta_mgz_lost = fields.Integer('Meta Magazine-Newspaper Lost', compute='_compute_statistics')

    pro = fields.Integer('Project', compute='_compute_statistics')
    meta_pro = fields.Integer('Meta Project', compute='_compute_statistics')
    meta_pro_lost = fields.Integer('Meta Project Lost', compute='_compute_statistics')

    @api.multi
    def _compute_statistics(self):
        Meta_books = self.env['lib.meta.books']
        Meta_mgzs = self.env['lib.meta.magazinenewspapers']
        Meta_pros = self.env['lib.meta.projects']
        for lib_st in self:
            lib_st.book = self.env['lib.book'].sudo().search_count([])
            lib_st.meta_book = Meta_books.sudo().search_count([])
            lib_st.meta_book_lost = Meta_books.sudo().search_count([('is_lost', '=', True)])
            lib_st.mgz = self.env['lib.magazine.newspaper'].sudo().search_count([])
            lib_st.meta_mgz = Meta_mgzs.sudo().search_count([])
            lib_st.meta_mgz_lost = Meta_books.sudo().search_count([('is_lost', '=', True)])
            lib_st.pro = self.env['lib.document.project'].sudo().search_count([])
            lib_st.meta_pro = Meta_pros.sudo().search_count([])
            lib_st.meta_pro_lost = Meta_pros.sudo().search_count([('is_lost', '=', True)])

