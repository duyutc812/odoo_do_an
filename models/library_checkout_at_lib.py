from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
import pytz


class CheckoutAtLib(models.Model):
    _name = 'library.checkout.at.lib'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Checkout In Lib'

    @api.model
    def _default_stage(self):
        return self.env['library.checkout.stage'].search([], limit=1)

    @api.model
    def _group_expand_stage_id(self, stages, domain, order):
        return stages.search([], order=order)

    card_id = fields.Many2one('library.card', string="Card ID",
                              required=True,
                              domain=[('state', '=', 'running'), ('is_penalty', '=', False)], track_visibility='always')
    state_card = fields.Selection(related='card_id.state', store=True, string='State Card')
    gt_name = fields.Char(related='card_id.gt_name', store=True, track_visibility='always')
    stage_id = fields.Many2one('library.checkout.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               track_visibility='always'
                               )
    state = fields.Selection(related='stage_id.state', store=True, string='State')
    name_seq = fields.Char(string="Checkout ID", default=lambda self: _('New'), readonly=True)
    borrow_date = fields.Datetime(string='Borrow Date', track_visibility='always')
    return_date = fields.Datetime(string='Return Date', track_visibility='always')
    type_document = fields.Selection([
        ('book', 'Book'),
        ('magazine', 'Magazine And Newspaper'),
        ('project', 'Project'),
    ], string='Type Document', default='book', required=True)
    book_id = fields.Many2one('library.book', 'Name Book')
    meta_book_id = fields.Many2one('meta.books', string='Meta Book')
    project_id = fields.Many2one('document.project', 'Name Project')
    meta_project_id = fields.Many2one('meta.projects', string='Meta Project')
    mgz_new_id = fields.Many2one('magazine.newspaper', 'Name Mgz/New', track_visibility='always')
    meta_mgz_new_id = fields.Many2one('meta.magazinenewspapers',
                                      string='Meta Mgz-New', track_visibility='always')
    status_document = fields.Text('Description', compute='_compute_status_document', store=True)
    price_doc = fields.Monetary("Price Doc", 'currency_id', compute='_compute_price_doc', store=True)
    user_id = fields.Many2one('res.users', 'Librarian',
                              default=lambda s: s.env.uid,
                              readonly=True, track_visibility='always')

    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda s: s.env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1))
    price_penalty = fields.Monetary('Penalty Price', 'currency_id')
    note = fields.Char('Note')
    is_lost_doc = fields.Boolean('Lost')

    @api.onchange('card_id')
    def onchange_card_id(self):
        if self.sudo().search([('card_id', '=', self.card_id.id),
                        ('state', '=', 'running'),
                        ('id', 'not in', self.ids)]):
            self.card_id = ''
            return {
                'warning': {
                    'title': _('Card ID'),
                    'message': _('You are borrowing a document, please return it to continue!'),
                }
            }

    @api.onchange('type_document')
    def onchange_type_document(self):
        if self.type_document == 'project':
            self.book_id = ''
            self.meta_book_id = ''
            self.mgz_new_id = ''
            self.meta_mgz_new_id = ''
        elif self.type_document == 'book':
            self.project_id = ''
            self.meta_project_id = ''
            self.mgz_new_id = ''
            self.meta_mgz_new_id = ''
        else:
            self.book_id = ''
            self.meta_book_id = ''
            self.project_id = ''
            self.meta_project_id = ''

    @api.depends('book_id', 'mgz_new_id', 'project_id')
    def _compute_price_doc(self):
        for chk in self:
            if chk.book_id:
                chk.price_doc = chk.book_id.price
            elif chk.mgz_new_id:
                chk.price_doc = chk.mgz_new_id.price
            elif chk.project_id:
                chk.price_doc = chk.project_id.price

    @api.onchange('book_id')
    def _onchange_book_id(self):
        self.meta_book_id = ''
        return {'domain': {'meta_book_id': [('state', '=', 'available'),
                                            ('book_id', '=', self.book_id.id)]}}

    @api.onchange('mgz_new_id')
    def _onchange_mgz_new_id(self):
        self.meta_mgz_new_id = ''
        return {'domain': {'meta_mgz_new_id': [('state', '=', 'available'),
                                               ('mgz_new_id', '=', self.mgz_new_id.id)]}}

    @api.onchange('project_id')
    def _onchange_project_id(self):
        self.meta_project_id = ''
        return {'domain': {'meta_project_id': [('state', '=', 'available'),
                                               ('project_id', '=', self.project_id.id)]}}

    @api.depends('meta_book_id', 'meta_mgz_new_id', 'meta_project_id')
    def _compute_status_document(self):
        for chk in self:
            if chk.meta_book_id:
                chk.status_document = chk.meta_book_id.description
            elif chk.meta_mgz_new_id:
                chk.status_document = chk.meta_mgz_new_id.description
            elif chk.meta_project_id:
                chk.status_document = chk.meta_project_id.description

    @api.constrains('card_id', 'book_id', 'mgz_new_id', 'project_id')
    def _constrains_card_id_book(self):
        lib_checkout = self.env['library.checkout.at.lib']
        domain = [('card_id', '=', self.card_id.id),
                  ('state', 'in', ['running', 'draft']),
                  ('book_id', '=', self.book_id.id),
                  ('mgz_new_id', '=', self.mgz_new_id.id),
                  ('project_id', '=', self.project_id.id),
                  ('id', 'not in', self.ids)]
        chk_of_card = lib_checkout.sudo().search(domain)
        if chk_of_card:
            raise ValidationError(_('You cannot borrow book to same card more than once!'))

        domain2 = [
            ('card_id', '=', self.card_id.id),
            ('state', '=', 'running'),
            ('id', '!=', self.id)
        ]
        checkout_of_card2 = lib_checkout.sudo().search_count(domain2)
        if checkout_of_card2:
            raise ValidationError(_('You have borrowed more than the specified number of books for each card'))

    @api.onchange('state')
    def _onchange_state(self):
        if self.state == 'draft':
            self.borrow_date = ''
            self.return_date = ''
        elif self.state == 'running':
            self.return_date = ''
        if self.state not in ['lost']:
            self.price_penalty = 0
            self.note = ''

    @api.multi
    def running_state(self):
        state_running = self.env['library.checkout.stage'].search([('state', '=', 'running')])
        for chk in self:
            if self.sudo().search([('card_id', '=', chk.card_id.id),
                            ('state', '=', 'running'),
                            ('id', 'not in', self.ids)]):
                raise ValidationError(_('You are borrowing a document, please return it to continue!'))
            chk.name_seq = self.env['ir.sequence'].next_by_code('library.checkout.sequence') or _('New')
            chk.stage_id = state_running
            chk._onchange_state()
            if chk.book_id:
                if chk.meta_book_id.state == 'available':
                    chk.meta_book_id.state = 'not_available'
                    chk.meta_book_id.checkout = str(chk.name_get()[0][1]) + ' - At lib'
                else:
                    raise ValidationError(_('Book: "%s - %s" have borrowed.' %
                                          (self.meta_book_id.name_seq, self.book_id.name)))
            elif chk.mgz_new_id:
                if self.meta_mgz_new_id.state == 'available':
                    self.meta_mgz_new_id.state = 'not_available'
                    chk.meta_mgz_new_id.checkout = str(chk.name_get()[0][1]) + ' - At lib'
                else:
                    raise ValidationError(_('Magazine/Newspaper have borrowed.'))
            elif chk.project_id:
                if chk.meta_project_id.state == 'available':
                    chk.meta_project_id.state = 'not_available'
                    chk.meta_project_id.checkout = str(chk.name_get()[0][1]) + ' - At lib'
                else:
                    raise ValidationError(_('Project: " %s " have borrowed.' % (self.project_id.name)))
            chk.borrow_date = fields.Datetime.now()
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Checkout Cofirmed .... Thank You',
                    'type': 'rainbow_man',
                }
            }

    @api.multi
    def draft_state(self):
        stage_draft = self.env['library.checkout.stage'].search([('state', '=', 'draft')])
        for chk in self:
            chk.stage_id = stage_draft
            chk._onchange_state()
            dic = {
                'state': 'available',
                'checkout': '',
            }
            if chk.book_id and chk.meta_book_id.state == 'not_available':
                chk.meta_book_id.write(dic)
            elif chk.mgz_new_id and chk.meta_mgz_new_id.state == 'not_available':
                chk.meta_mgz_new_id.write(dic)
            elif chk.project_id and chk.meta_project_id.state == 'not_available':
                chk.meta_project_id.write(dic)

    @api.multi
    def done_state(self):
        stage_done = self.env['library.checkout.stage'].search([('state', '=', 'done')])
        for chk in self:
            chk.stage_id = stage_done
            chk._onchange_state()
            dic = {
                'state': 'available',
                'checkout': '',
            }
            if chk.book_id:
                chk.meta_book_id.write(dic)
            elif chk.mgz_new_id:
                chk.meta_mgz_new_ide.write(dic)
            elif chk.project_id:
                chk.meta_project_id.write(dic)
            chk.return_date = fields.Datetime.now()

    @api.multi
    def fined_state(self):
        stage_fined = self.env['library.checkout.stage'].search([('state', '=', 'fined')])
        for chk in self:
            chk.stage_id = stage_fined
            chk._onchange_state()
            dic = {
                'state': 'available',
                'checkout': '',
            }
            if chk.book_id:
                chk.meta_book_id.write(dic)
            elif chk.mgz_new_id:
                chk.meta_mgz_new_id.write(dic)
            elif chk.project_id:
                chk.meta_project_id.write(dic)
            chk.return_date = fields.Datetime.now()
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'library.checkout.at.lib',
                'res_id': chk.id,
                'context': context
            }

    @api.multi
    def lost_document(self):
        stage_lost = self.env['library.checkout.stage'].search([('state', '=', 'lost')])
        for chk in self:
            chk.stage_id = stage_lost
            chk._onchange_state()
            dic = {
                'is_lost': True,
                'checkout': str(chk.name_get()[0][1]) + _(' - At lib'),
                'state': 'not_available',
            }
            if chk.book_id:
                chk.meta_book_id.write(dic)
                chk.note = _('lost document: %s') % (str(chk.meta_book_id.name_seq))
            elif chk.mgz_new_id:
                chk.meta_mgz_new_id.write(dic)
                chk.note = _('lost document: %s') % (str(chk.meta_mgz_new_id.name_seq))
            elif chk.project_id:
                chk.meta_project_id.write(dic)
                chk.note = _('lost document: %s') % (str(chk.meta_project_id.name_seq))
            chk.return_date = fields.Datetime.now()
            chk.price_penalty = chk.price_doc

    @api.multi
    def cancel_state(self):
        stage_done = self.env['library.checkout.stage'].search([('state', '=', 'done')])
        for chk in self:
            chk.stage_id = stage_done
            chk._onchange_state()
            dic = {
                'state': 'available',
                'checkout': '',
                'description': chk.status_document,
                'is_lost': False,
            }
            if chk.book_id:
                chk.meta_book_id.write(dic)
            elif chk.mgz_new_id:
                chk.meta_mgz_new_id.write(dic)
            elif chk.project_id:
                chk.meta_project_id.write(dic)
            chk.return_date = fields.Datetime.now()

    def borrow_back_home(self):
        chk_bh_obj = self.env['library.checkout.back.home']
        for chk in self:
            if chk.type_document == 'magazine':
                raise ValidationError('Khong the muon ve nha')
            else:
                vals={}
                vals.update({
                    'card_id': chk.card_id.id,
                    'type_document': chk.type_document,
                })
                if chk.book_id:
                    vals.update({
                        'book_id': chk.book_id.id,
                        'meta_book_id': chk.meta_book_id.id,
                    })
                elif chk.project_id:
                    vals.update({
                        'project_id': chk.project_id.id,
                        'meta_project_id': chk.meta_project_id.id,
                    })
            chk_bh = chk_bh_obj.create(vals)
            return {'name': _('Borrow Back Home'),
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_id': chk_bh.id,
                    'res_model': 'library.checkout.back.home',
                    'type': 'ir.actions.act_window',
                    'target': 'new'}

    @api.multi
    def name_get(self):
        res = []
        for chk in self:
            res.append((chk.id, '%s - %s' % (chk.name_seq, chk.gt_name)))
        return res

    def unlink(self):
        for chk in self:
            if chk.state != 'draft':
                raise ValidationError(_('You can not delete checkout when state not is draft!'))
        return super(CheckoutAtLib, self).unlink()

    @api.multi
    def print_report(self):
        return self.env.ref('do_an_tn.action_library_checkout_at_lib_penalty').report_action(self)



