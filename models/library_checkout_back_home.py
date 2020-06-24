from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date


class CheckoutBackHome(models.Model):
    _name = 'library.checkout.back.home'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Checkout Back Home'

    @api.model
    def _default_stage(self):
        return self.env['library.checkout.stage'].search([], limit=1)

    @api.model
    def _group_expand_stage_id(self, stages, domain, order):
        return stages.search([], order=order)

    stage_id = fields.Many2one('library.checkout.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               )
    state = fields.Selection(related='stage_id.state', store=True)

    card_id = fields.Many2one('library.card', string="Card No",
                              required=True,
                              domain=[('state', '=', 'running')])
    state_card = fields.Selection(related='card_id.state', store=True)
    user_id = fields.Many2one('res.users', 'Librarian',
                              default=lambda s: s.env.uid,
                              readonly=True)
    borrow_date = fields.Datetime(default=fields.Datetime.now(), string="Borrow date", readonly=True)
    name_seq = fields.Char(string="Checkout ID", default=lambda self: _('New'), readonly=True)

    # limit_book_card = fields.Integer(related='card_id.book_limit', string='Book limit on card')
    gt_name = fields.Char(related='card_id.gt_name', string='The user\'s card')
    start_date = fields.Date(related='card_id.start_date', string='Start date')
    end_date = fields.Date(related='card_id.end_date', string='End Date')
    book_limit_card = fields.Integer(related='card_id.book_limit', store=True)
    limit_syllabus_card = fields.Integer(related='card_id.limit_syllabus', store=True)
    type_document = fields.Selection([
        ('book', 'Book'),
        ('project', 'Project'),
    ], string='Type Document', default='book', required=True)

    book_id = fields.Many2one('library.book', 'Name Book',
                              domain=[('state', '=', 'available')])
    meta_book_id = fields.Many2one('meta.books', string='Meta Book')
    project_id = fields.Many2one('document.project', 'Name Project', domain=[('state', '=', 'available')])
    meta_project_id = fields.Many2one('meta.projects', string='Meta Project')
    status_document = fields.Text('Description', compute='_compute_status_document_price_doc', store=True)
    category_book = fields.Many2one(related='book_id.category', store=True)
    price_doc = fields.Monetary("Price Doc", 'currency_id', compute='_compute_status_document_price_doc', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda s: s.env['res.currency'].search([('name', '=', 'VND')], limit=1))
    price = fields.Monetary('Price', 'currency_id')
    note = fields.Char('Note')
    return_date = fields.Date(string="")

    @api.onchange('type_document')
    def onchange_type_document(self):
        if self.type_document == 'project':
            self.book_id = ''
            self.meta_book_id = ''
        elif self.type_document == 'book':
            self.project_id = ''
            self.meta_project_id = ''

    @api.onchange('book_id')
    def _onchange_book_id(self):
        self.meta_book_id = ''
        return {'domain': {'meta_book_id': [('state', '=', 'available'),
                                            ('book_id', '=', self.book_id.id)]}}

    @api.onchange('project_id')
    def _onchange_project_id(self):
        self.meta_project_id = ''
        return {'domain': {'meta_project_id': [('state', '=', 'available'),
                                               ('project_id', '=', self.project_id.id)]}}

    @api.depends('meta_book_id', 'book_id', 'meta_project_id', 'project_id')
    def _compute_status_document_price_doc(self):
        for chk in self:
            if chk.meta_book_id:
                chk.status_document = chk.meta_book_id.description
                chk.price_doc = chk.book_id.price
            elif chk.meta_project_id:
                chk.status_document = chk.meta_project_id.description
                chk.price_doc = chk.project_id.price

    # @api.model
    # def create(self, vals):
    #     if vals.get('card_id'):
    #         # fetch the record of user type student
    #         card = self.env['library.card'].browse(vals.get('card_id'))
    #         vals.update({'state_card': card.state,
    #                      'card_id': card.id,
    #                      'gt_name': card.gt_name,
    #                      'start_date': card.start_date,
    #                      'end_date': card.end_date,
    #                      'book_limit_card': card.book_limit,
    #                      'limit_syllabus_card': card.limit_syllabus,
    #                      })
    #
    #     return super(CheckoutBackHome, self).create(vals)
    #
    # @api.multi
    # def write(self, vals):
    #     if vals.get('card_id'):
    #         card = self.env['library.card'].browse(vals.get('card_id'))
    #         vals.update({'state_card': card.state,
    #                      'card_id': card.id,
    #                      'gt_name': card.gt_name,
    #                      'start_date': card.start_date,
    #                      'end_date': card.end_date,
    #                      'book_limit_card': card.book_limit,
    #                      'limit_syllabus_card': card.limit_syllabus,
    #                      })
    #     return super(CheckoutBackHome, self).write(vals)
