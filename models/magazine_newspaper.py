from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Magazine(models.Model):
    _name = 'magazine.newspaper'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Magazine and newspaper'

    type_mgz_new = fields.Selection([
        ('magazine', 'Magazine'),
        ('newspaper', 'Newspaper')
    ], string='Type', default='newspaper', required=True, track_visibility='always')
    image = fields.Binary('Cover')
    category_mgz = fields.Many2one('categories.magazine', string='Category Magazine', track_visibility='always')
    category_new = fields.Many2one('categories.newspaper', string='Category Newspaper', track_visibility='always')
    num_mgz_new = fields.Integer(string="No.", track_visibility='always')
    publish_date = fields.Date(string='Publish Date', required=True, track_visibility='always')
    publish_year = fields.Integer(compute='get_publish_year', store=True, track_visibility='always')
    rack = fields.Many2one('library.rack', 'Rack', track_visibility='always', required=True)

    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda s: s.env['res.currency'].search([('name', '=', 'VND')], limit=1))
    price = fields.Monetary('Price', 'currency_id')

    quantity = fields.Integer(string='Quantity', compute='get_quantity_remaining')
    remaining = fields.Integer(string='Remaining', compute='get_quantity_remaining')
    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', compute='get_quantity_remaining')

    meta_mgz_new_ids = fields.One2many(
        'meta.magazinenewspapers',
        'mgz_new_id', track_visibility='always'
    )
    active = fields.Boolean('Active?', default=True)

    @api.constrains('price')
    def _constrains_price(self):
        for mg_new in self:
            if mg_new.price <= 0:
                raise ValidationError('The price must be greater than 0!')

    @api.depends('publish_date')
    def get_publish_year(self):
        for mgz in self:
            mgz.publish_year = mgz.publish_date.year if mgz.publish_date else ''

    @api.onchange('type_mgz_new')
    def _onchange_type_mgz_new(self):
        if self.type_mgz_new == 'magazine':
            self.category_new = ''
        else:
            self.category_mgz = ''
        self.num_mgz_new = ''
        self.publish_date = ''
        self.rack = ''
        self.price = ''

    @api.depends('meta_mgz_new_ids')
    def get_quantity_remaining(self):
        for mgz_new in self:
            mgz_new.quantity = len(mgz_new.meta_mgz_new_ids)
            mgz_new.remaining = len(mgz_new.meta_mgz_new_ids.filtered(
                lambda a: a.state == 'available'
            ))

            mgz_new.state = 'not_available'
            if mgz_new.remaining >= 1:
                mgz_new.state = 'available'
            print(mgz_new.state)
        print('depends')
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
            res.append((rec.id, '%s %s - No.%s'
                        % ('Newspaper' if rec.type_mgz_new == 'newspaper' else 'Magazine',
                           rec.category_mgz.name if rec.category_mgz else rec.category_new.name, rec.num_mgz_new)))
        return res

    def unlink(self):
        for mg_new in self:
            if len(mg_new.meta_mgz_new_ids):
                raise ValidationError('You cannot delete !')
            return super(Magazine, self).unlink()

    _sql_constraints = [
        ('unique_category_magazine_num',
         'unique(category_mgz, num_mgz_new , publish_year)',
         'No. Magazine\'s in year does already exist'),
        ('unique_category_newspaper_num',
         'unique(category_new, num_mgz_new , publish_year)',
         'No. Newspaper\'s in year does already exist'),
        ('mgz_new_check_date',
         'CHECK (publish_date <= current_date)',
         'The Published Date must be less than the current date'),
    ]


class MetaMagazineNewspaper(models.Model):
    _name = 'meta.magazinenewspapers'
    _description = 'Meta Magazine/Newspaper'

    mgz_new_id = fields.Many2one('magazine.newspaper', string='Magazine/Newspaper', track_visibility='always')
    name_seq = fields.Char(string="Meta Magazine/Newspaper ID", default=lambda self: _('New'), readonly=True)
    description = fields.Text('Description',default='Tài liệu mới', track_visibility='always')
    sequence = fields.Integer()
    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', default='available')
    chk_mg_new_id = fields.Many2one('library.checkout.magazine.newspaper', string='Checkout ID', readonly=True)
    is_lost = fields.Boolean('Lost', default=False)
    is_active = fields.Boolean('Active', default=True)

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
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('library.meta.magazine.newspaper.sequence') or _(
                'New')
        result = super(MetaMagazineNewspaper, self).create(vals)
        return result

    def unlink(self):
        chk_mg_new = self.env['library.checkout.magazine.newspaper']
        for meta_mg in self:
            if meta_mg.chk_mg_new_id:
                raise ValidationError('You cannot delete record %s!' %(meta_mg.name_seq))
            if chk_mg_new.search([('meta_mgz_new_id', '=', meta_mg.id)]):
                raise ValidationError('Related checkout magazine newspaper record . You can not delete!')
        return super(MetaMagazineNewspaper, self).unlink()
