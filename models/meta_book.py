from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MetaBook(models.Model):
    _name = 'meta.books'
    _description = 'Meta book'

    book_id = fields.Many2one('library.book', string='Book')
    name_seq = fields.Char(string="Meta Book ID", default=lambda self: _('New'), readonly=True)
    description = fields.Text('Description', default='Tài liệu mới')
    sequence = fields.Integer()
    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', default='available')
    checkout = fields.Char(readonly=True)
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
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('library.meta.books.sequence') or _('New')
        result = super(MetaBook, self).create(vals)
        return result

    def unlink(self):
        chk_lib = self.env['library.checkout.at.lib']
        chk_bh = self.env['library.checkout.back.home']
        for book in self:
            if book.checkout or chk_lib.sudo().search([('meta_book_id', '=', book.id)]) or chk_bh.search([('meta_book_id', '=', book.id)]):
                raise ValidationError(_('You cannot delete record %s!' % (book.name_seq)))
            return super(MetaBook, self).unlink()