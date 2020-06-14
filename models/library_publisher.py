from odoo import api, fields, models, _


class Publisher(models.Model):
    _name = 'library.publisher'
    _description = 'Publisher'

    name_seq = fields.Char(string='Publisher ID', required=True, copy=False, readonly=True, index=True,
                           default=lambda self: _('New'))
    name = fields.Char('Publisher')
    publisher_image = fields.Binary('Cover')
    address = fields.Text('Address')

    phone = fields.Text('Phone')
    fax = fields.Text('Fax')
    email = fields.Char('Email')
    founding = fields.Char('Founding')
    website = fields.Char('Website')
    website2 = fields.Char('Website 2')
    note = fields.Html('Notes')
    facebook = fields.Char('Facebook')
    book_ids = fields.One2many('library.book', 'publisher_id')

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('library.publisher.sequence') or _('New')
        result = super(Publisher, self).create(vals)
        return result

    @api.onchange('name')
    def _onchange_name_publisher(self):
        """Method to set upper for name"""
        for pub in self:
            pub.name = pub.name.title() if pub.name else ''