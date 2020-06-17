from odoo import api, fields, models, _


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