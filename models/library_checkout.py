from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Checkout(models.Model):
    _name = 'library.checkout'
    _description = 'Library Checkout'
    _rec_name = 'name_seq'

    card_id = fields.Many2one('library.card', string="Card No",
                              required=True,
                              domain="[('state', '=', 'running')]")
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

    borrow_book = fields.Many2one('library.book', 'Book Name',
                                  domain=[('is_available', '=', 'avai')],
                                  required=True)
    note = fields.Char('Note', readonly=True)
    count = fields.Integer(compute='_compute_get_another_checkout_of_card')

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s - %s' % (rec.name_seq, rec.gt_name)))
        return res

    @api.multi
    def running(self):
        if self.name_seq == 'New':
            self.name_seq = self.env['ir.sequence'].next_by_code('library.checkout.sequence') or _('New')

        self.stage_id = self.env['library.checkout.stage'].search([
            ('state', '=', 'running')
        ])
        if self.borrow_book.is_available == 'avai':
            self.borrow_book.is_available = 'not_avai'
        else:
            raise ValidationError('Book: %s have borrowed.' %(self.borrow_book.book_name))
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
        self.borrow_book.is_available = 'avai'
        self.return_date = fields.Date.today()

    def unlink(self):
        for rec in self:
            if rec.state == 'running' or rec.state == 'done' or rec.state == 'fined':
                raise ValidationError('You can not delete checkout when state is borrowed, returned, fined')

        return super(Checkout, self).unlink()

    @api.constrains('card_id', 'borrow_book')
    def _constrains_card_id_book(self):
        domain = [('card_id', '=', self.card_id.id),
                  ('state', '!=', 'done'),
                  ('borrow_book', '=', self.borrow_book.id),
                  ('id', 'not in', self.ids)]
        print(self.card_id.book_limit)
        checkout_of_card = self.env['library.checkout'].search(domain)
        domain2 = [
            ('card_id', '=', self.card_id.id),
            ('state', '=', 'running'),
            ('id', '!=', self.id)
        ]
        checkout_of_card2 = self.env['library.checkout'].search_count(domain2)
        print(checkout_of_card2)
        if self.card_id.book_limit <= checkout_of_card2:
            raise ValidationError('You have borrowed more than the specified number of books for each card')
        if checkout_of_card:
            raise ValidationError('You cannot borrow book to same card more than once!')

    @api.multi
    def lost_book(self):
        self.stage_id = self.env['library.checkout.stage'].search([
            ('state', '=', 'fined')])
        self.note = 'Fined because lost book'
        self.return_date = fields.Date.today()

    def _compute_get_another_checkout_of_card(self):
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

    # @api.multi
    # def write(self, vals):
    #     if self.state != vals['state']:
    #         raise ValidationError('khong the thay doi')

    # @api.multi
    # def write(self, vals):
    #     print(self.state)
    #     print(vals['state'])
    #     if self.state == 'draft' and vals['state'] == 'running':
    #         # print('abc')
    #         # vals['name_seq'] = self.env['ir.sequence'].next_by_code('library.checkout.sequence') or _('New')
    #         #
    #         # vals['state'] = 'running'
    #         # if self.borrow_book.is_available == 'avai':
    #         #     vals['borrow_book.is_available'] = 'not_avai'
    #         # else:
    #         #     raise ValidationError('Book: %s have borrowed.' % (self.borrow_book.book_name))
    #         raise ValidationError('can not change state from fined to draft')
    #     if self.state == 'running' and vals['state'] == 'draft':
    #         raise ValidationError('can not change state from borrowed to draft')
    #     if self.state == 'done' and vals['state'] == 'draft':
    #         raise ValidationError('can not change state from returned to draft')
    #     if self.state == 'fined' and vals['state'] == 'draft':
    #         raise ValidationError('can not change state from fined to draft')
    #     super(Checkout, self).write(vals)
    #     return True






