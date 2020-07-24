from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Magazine(models.Model):
    _name = 'lib.magazine.newspaper'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Tạp chí - báo'

    type_mgz_new = fields.Selection([
        ('magazine', 'Tạp chí'),
        ('newspaper', 'Báo')
    ], string='Loại', default='newspaper', required=True, track_visibility='always')
    image = fields.Binary('Ảnh')
    category_mgz_id = fields.Many2one('lib.category.magazine', string='Thể loại tạp chí', track_visibility='always')
    category_new_id = fields.Many2one('lib.category.newspaper', string='Thể loại báo', track_visibility='always')
    num_mgz_new = fields.Integer(string="Số tạp chí/báo", track_visibility='always')
    publish_date = fields.Date(string='Ngày xuất bản', required=True, track_visibility='always')
    publish_year = fields.Integer(compute='get_publish_year', store=True, track_visibility='always')
    rack = fields.Many2one('lib.rack', 'Giá chứa', track_visibility='always', required=True)

    currency_id = fields.Many2one('res.currency', 'Tiền tệ',
                                  default=lambda s: s.env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1))
    price = fields.Monetary('Giá tiền', 'currency_id')

    quantity = fields.Integer(string='Số lượng', compute='_compute_quantity_remaining', store=True)
    remaining = fields.Integer(string='Còn lại', compute='_compute_quantity_remaining', store=True)
    state = fields.Selection([
        ('available', 'Có sẵn'),
        ('not_available', 'Không có sẵn')
    ], string='Status', compute='_compute_quantity_remaining', store=True)
    is_active = fields.Boolean('Có hiệu lực?', default=True)
    meta_mgz_new_ids = fields.One2many(
        'lib.meta.magazinenewspapers',
        'mgz_new_id', track_visibility='always'
    )

    @api.constrains('price')
    def _constrains_price(self):
        for mg_new in self:
            if mg_new.price <= 0:
                raise ValidationError(_('Giá tiền phải lớn hơn 0!'))

    @api.depends('publish_date')
    def get_publish_year(self):
        for mgz in self:
            mgz.publish_year = mgz.publish_date.year if mgz.publish_date else ''

    @api.onchange('type_mgz_new')
    def _onchange_type_mgz_new(self):
        if self.type_mgz_new == 'magazine':
            self.category_new_id = ''
        else:
            self.category_mgz_id = ''
        self.num_mgz_new = ''
        self.publish_date = ''
        self.rack = ''
        self.price = ''

    @api.depends('meta_mgz_new_ids')
    def _compute_quantity_remaining(self):
        for mgz_new in self:
            mgz_new.quantity = len(mgz_new.meta_mgz_new_ids)
            mgz_new.remaining = len(mgz_new.meta_mgz_new_ids.filtered(
                lambda a: a.state == 'available'
            ))

            mgz_new.state = 'not_available'
            if mgz_new.remaining >= 1:
                mgz_new.state = 'available'
        return True

    # @api.depends('books_available')
    # def _compute_state(self):
    #     for mgz_new in self:
    #         mgz_new.state = 'not_available'
    #         if mgz_new.books_available >= 1:
    #             mgz_new.state = 'available'
    #         print(mgz_new.state)
    #     return True

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s %s - Số %s'
                        % ('Báo' if rec.type_mgz_new == 'newspaper' else 'Tạp chí',
                           rec.category_mgz_id.name if rec.category_mgz_id else rec.category_new_id.name, rec.num_mgz_new)))
        return res

    def unlink(self):
        for mg_new in self:
            if len(mg_new.meta_mgz_new_ids):
                raise ValidationError(_('Bạn không thể xoá !'))
            return super(Magazine, self).unlink()

    _sql_constraints = [
        ('unique_category_magazine_num',
         'unique(category_mgz_id, num_mgz_new , publish_year)',
         'Số tap chí của thể loại tạp chí này trong năm này đã tồn tại!'),
        ('unique_category_newspaper_num',
         'unique(category_new_id, num_mgz_new , publish_year)',
         'Số báo của thể loại báo này trong năm này đã tồn tại!'),
        ('mgz_new_check_date',
         'CHECK (publish_date <= current_date)',
         'Ngày xuất bản phải nhỏ hơn ngày hiện tại!'),
    ]


class MetaMagazineNewspaper(models.Model):
    _name = 'lib.meta.magazinenewspapers'
    _description = 'Meta Tạp chí - báo'

    name_seq = fields.Char(string="Mã meta tạp chí/báo", default=lambda self: _('New'), readonly=True)
    mgz_new_id = fields.Many2one('lib.magazine.newspaper', string='Tạp chí-báo', track_visibility='always')
    description = fields.Text('Tình trạng', default='Tài liệu mới', track_visibility='always')
    sequence = fields.Integer()
    state = fields.Selection([
        ('available', 'Có sẵn'),
        ('not_available', 'Không có sẵn')
    ], string='Trạng thái', default='available')
    checkout = fields.Char('Phiếu mượn')
    is_lost = fields.Boolean('Đã mất', default=False)
    is_active = fields.Boolean('Có hiệu lực', default=True)

    @api.onchange('is_lost')
    def onchange_is_lost(self):
        for mg_new in self:
            if mg_new.is_lost:
                mg_new.state = 'not_available'

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s' %
                        (rec.name_seq)))
                         # rec.mgz_new_id.category_mgz.name if rec.mgz_new_id.category_mgz
                         # else rec.mgz_new_id.category_new.name,
                         # rec.mgz_new_id.num_mgz_new)))
        return res

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('lib.meta.magazine.newspaper.sequence') or _(
                'New')
        result = super(MetaMagazineNewspaper, self).create(vals)
        return result

    def unlink(self):
        for meta_mg in self:
            if meta_mg.checkout:
                raise ValidationError(_('Bạn không thể xoá: %s khi meta tạp chí - báo đang được mượn!' %(meta_mg.name_seq)))
        return super(MetaMagazineNewspaper, self).unlink()
