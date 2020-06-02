from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Checkout(models.Model):
    _name = 'library.checkout'
    _description = 'Library Checkout'

    card_id = fields.Many2one('library.card', string="Card No",
                              required=True,
                              domain=[('state', '=', 'running')])
    user_id = fields.Many2one('res.users', 'Librarian',
                              default=lambda s: s.env.uid,
                              readonly=True)
    request_date = fields.Date(default=fields.Date.today(), readonly=True)

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

    name_seq = fields.Char(string="Checkout ID", default=lambda self: _('New'), readonly=True)

    limit_book_card = fields.Integer(related='card_id.book_limit', string='Book limit on card')
    gt_name = fields.Char(related='card_id.gt_name', string='The user\'s card')
    start_date = fields.Date(related='card_id.start_date', string='Start date')
    duration = fields.Selection(related='card_id.duration', string='Duration')
    end_date = fields.Date(related='card_id.end_date', string='End Date')
    state_card = fields.Selection(related='card_id.state', string='Status card', readonly=True, store=True)

    return_date = fields.Date(string='Return Date', readonly=True)
    type_document = fields.Selection([
        ('book', 'Book'),
        ('magazine', 'Magazine And Newspaper'),
        ('project', 'Project'),
    ], string='Type Document', default='book')

    book_id = fields.Many2one('meta.books', 'Name Book',
                              domain=[('state', '=', 'available')])
    # meta_book_id = fields.Many2one('meta.books', string='Meta Book')
    # magazine_id = fields.Many2one('meta.magazinenewspaper', 'Name Magazine',
    #                               domain=[('state', '=', 'available')])
    # project_id = fields.Many2one('document.project', 'Name Project',
    #                              domain=[('sta', '=', 'available')])
    status_document = fields.Text('Status', compute='_compute_status_document', store=True)

    note = fields.Char('Note', readonly=True)
    count = fields.Integer(compute='_compute_another_chk')

    # @api.onchange('book_id')
    # def _onchange_book_id(self):
    #     for chk in self:
    #         chk.meta_book_id = ''
    #         return {'domain': {'meta_book_id': [('state', '=', 'available')]}}

    @api.depends('book_id')
    def _compute_status_document(self):
        for chk in self:
            if chk.book_id:
                chk.status_document = chk.book_id.description
            # elif document.magazine_id:
            #     document.status_document = document.magazine_id.status

    def unlink(self):
        for chk in self:
            if chk.state == 'running' or chk.state == 'done' or chk.state == 'fined':
                raise ValidationError('You can not delete checkout when state is borrowed, returned, fined')

        return super(Checkout, self).unlink()

    @api.multi
    def name_get(self):
        res = []
        for chk in self:
            res.append((chk.id, '%s - %s' % (chk.name_seq, chk.gt_name)))
        return res

    @api.constrains('card_id', 'book_id')
    def _constrains_card_id_book(self):
        lib_checkout = self.env['library.checkout']
        domain = [('card_id', '=', self.card_id.id),
                  ('state', '!=', 'done'),
                  ('book_id', '=', self.book_id.id),
                  # ('magazine_id', '=', self.magazine_id.id),
                  # ('project_id', '=', self.project_id.id),
                  ('id', 'not in', self.ids)]
        chk_of_card = lib_checkout.search(domain)
        if chk_of_card:
            raise ValidationError('You cannot borrow book to same card more than once!')

        # domain2 = [
        #     ('card_id', '=', self.card_id.id),
        #     ('state', '=', 'running'),
        #     ('id', '!=', self.id)
        # ]
        # checkout_of_card2 = self.env['library.checkout'].search_count(domain2)
        # print(checkout_of_card2)
        # if self.card_id.book_limit <= checkout_of_card2:
        #     raise ValidationError('You have borrowed more than the specified number of books for each card')

    @api.multi
    def running(self):
        if self.name_seq == 'New':
            self.name_seq = self.env['ir.sequence'].next_by_code('library.checkout.sequence') or _('New')

        self.stage_id = self.env['library.checkout.stage'].search([
            ('state', '=', 'running')
        ])
        if self.book_id:
            if self.book_id.state == 'available':
                self.book_id.state = 'not_available'
            else:
                raise ValidationError('Book: "%s" have borrowed.' % (self.book_id.book_name))
        # if self.magazine_id:
        #     if self.magazine_id.is_available == 'available':
        #         self.magazine_id.is_available = 'not_available'
        #     else:
        #         raise ValidationError('Magazine/Newspaper have borrowed.')
        #
        # if self.project_id:
        #     if self.project_id.availability == 'available':
        #         self.project_id.availability = 'not_available'
        #     else:
        #         raise ValidationError('Project: " %s " have borrowed.' % (self.project_id.name))

        return {
            'effect': {
                    'fadeout': 'slow',
                    'message': 'Checkout Cofirmed .... Thank You',
                    'type': 'rainbow_man',
                }
        }

    def done(self):
        self.stage_id = self.env['library.checkout.stage'].search([
            ('state', '=', 'done')
        ])
        if self.book_id:
            self.book_id.states = 'available'
        # elif self.magazine_id:
        #     self.magazine_id.is_available = 'available'
        # elif self.project_id:
        #     self.project_id.availability = 'available'
        self.return_date = fields.Date.today()

    @api.multi
    def lost_book(self):
        self.stage_id = self.env['library.checkout.stage'].search([
            ('state', '=', 'fined')])
        self.note = 'Fined because lost book'
        self.return_date = fields.Date.today()

    def _compute_another_chk(self):
        domain = [
            ('card_id', '=', self.card_id.id),
            ('state', '=', 'running'),
            ('id', '!=', self.id)
        ]
        self.count = self.env['library.checkout'].search_count(domain)

    def open_checkout_of_card(self):
        return {
            'name': _('Another Checkout (running)'),
            'domain': [('card_id', '=', self.card_id.id),
                       ('state', '=', 'running'),
                       ('id', '!=', self.id)],
            'view_type': 'form',
            'res_model': 'library.checkout',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }







