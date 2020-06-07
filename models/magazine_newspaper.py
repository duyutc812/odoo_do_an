from odoo import api, fields, models, _


class Magazine(models.Model):
    _name = 'magazine.newspaper'
    _description = 'Magazine and newspaper'

    type_mgz_new = fields.Selection([
        ('magazine', 'Magazine'),
        ('newspaper', 'Newspaper')
    ], string='Type', default='newspaper', required=True)
    image = fields.Binary('Cover')
    category_mgz = fields.Many2one('categories.magazine', string='Category Magazine')
    category_new = fields.Many2one('categories.newspaper', string='Category Newspaper')
    num_mgz_new = fields.Integer(string="No.")
    publish_date = fields.Date(string='Publish Date', required=True)
    publish_year = fields.Integer(compute='get_publish_year', store=True)

    quantity = fields.Integer(string='Quantity', compute='get_quantity_remaining', store=True)
    remaining = fields.Integer(string='Actually', compute='get_quantity_remaining', store=True)

    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', compute='_compute_state', store=True)

    meta_mgz_new_ids = fields.One2many(
        'meta.magazinenewspapers',
        'mgz_new_id',
    )
    active = fields.Boolean('Active?', default=True)

    @api.depends('publish_date')
    def get_publish_year(self):
        for mgz in self:
            mgz.publish_year = mgz.publish_date.year if mgz.publish_date else ''

    @api.onchange('type_mgz_new')
    def _onchange_type_mgz_new(self):
        for r in self:
            if r.type_mgz_new == 'magazine':
                r.category_new = ''
            else:
                r.category_mgz = ''

    @api.depends('meta_mgz_new_ids')
    def get_quantity_remaining(self):
        for mgz_new in self:
            mgz_new.quantity = len(mgz_new.meta_mgz_new_ids)
            mgz_new.remaining = len(mgz_new.meta_mgz_new_ids.filtered(
                lambda a: a.state == 'available'
            ))

    @api.depends('remaining')
    def _compute_state(self):
        for mgz_new in self:
            mgz_new.state = 'available' if mgz_new.remaining > 0 else 'not_available'

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s %s - No.%s'
                        % ('Newspaper' if rec.type_mgz_new == 'newspaper' else 'Magazine',
                           rec.category_mgz.name if rec.category_mgz else rec.category_new.name, rec.num_mgz_new)))
        return res

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

    mgz_new_id = fields.Many2one('magazine.newspaper', string='Magazine/Newspaper')
    name_seq = fields.Char(string="Meta Magazine/Newspaper ID", default=lambda self: _('New'), readonly=True)
    description = fields.Text('Description')
    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', default='available')

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
