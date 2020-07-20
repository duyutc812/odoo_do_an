from odoo import api, fields, models, _


class Publisher(models.Model):
    _name = 'lib.publisher'
    _description = 'Nhà xuất bản'

    name_seq = fields.Char(string='Mã NXB', required=True, copy=False, readonly=True, index=True,
                           default=lambda self: _('New'))
    name = fields.Char('Tên nhà xuất bản')
    publisher_image = fields.Binary('Ảnh')
    address = fields.Text('Địa chỉ')

    phone = fields.Text('Số điện thoại')
    fax = fields.Text('Fax')
    email = fields.Char('Email')
    founding = fields.Char('Thành lập')
    website = fields.Char('Website')
    website2 = fields.Char('Website 2')
    facebook = fields.Char('Facebook')
    note = fields.Text('Ghi chú')
    book_ids = fields.One2many('lib.book', 'publisher_id', string="Tất cả sách")

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