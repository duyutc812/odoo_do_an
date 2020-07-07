from odoo import api, fields, models, _


class Publisher(models.Model):
    _name = 'lib.publisher'
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
    facebook = fields.Char('Facebook')
    note = fields.Text('Note')
    book_ids = fields.One2many('lib.book', 'publisher_id')

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('lib.publisher.sequence') or _('New')
        result = super(Publisher, self).create(vals)
        return result

    @api.onchange('name')
    def _onchange_name_publisher(self):
        """Method to set upper for name"""
        self.name = self.name.title() if self.name else ''