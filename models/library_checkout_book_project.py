from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError
from datetime import datetime, date
import pytz


class CheckoutBookProject(models.Model):
    _name = 'checkout.book.project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Checkout Book Project'

    @api.model
    def _default_stage(self):
        return self.env['library.checkout.stage'].search([], limit=1)

    @api.model
    def _group_expand_stage_id(self, stages, domain, order):
        return stages.search([], order=order)

    name_seq = fields.Char(string="Checkout ID", default=lambda self: _('New'), readonly=True)

    card_id = fields.Many2one('library.card', string="Card No",
                              required=True,
                              domain=[('state', '=', 'running'), ('is_penalty', '=', False)], track_visibility='always')
    gt_name = fields.Char(related='card_id.gt_name', store=True, track_visibility='always')
    stage_id = fields.Many2one('library.checkout.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               track_visibility='always')
    num_document = fields.Integer('Num document on card', default = 2)
    state = fields.Selection(related='stage_id.state', store=True)
    borrow_date = fields.Datetime(string='Request Date', track_visibility='always')
    checkout_book_line_ids = fields.One2many('checkout.book.line', 'checkout_id')
    checkout_project_line_ids = fields.One2many('checkout.project.line', 'checkout_id')
    user_id = fields.Many2one('res.users', 'Librarian',
                              default=lambda s: s.env.uid,
                              readonly=True, track_visibility='always')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda s: s.env['res.currency'].search([('name', '=', 'VND')], limit=1))
    price = fields.Monetary('Price', 'currency_id')
    note = fields.Char('Note')

    @api.constrains('card_id')
    def _constrain_card_id(self):
        chk_mg_new = self.env['library.checkout.magazine.newspaper']
        for chk in self:
            if chk_mg_new.search([('card_id', '=', chk.card_id.id),
                                  ('state', '=', 'running')]):
                raise ValidationError('Checkout magazine newspaper exists. Please return the document to continue!')
            if self.search([('card_id', '=', chk.card_id.id),
                            ('state', 'in', ['draft', 'running']),
                            ('id', 'not in', chk.ids)]):
                raise ValidationError('You cannot borrow Book or Project to same card more than once!')

    @api.multi
    def name_get(self):
        res = []
        for chk_mg_new in self:
            res.append((chk_mg_new.id, '%s - %s' % (chk_mg_new.name_seq, chk_mg_new.gt_name)))
        return res

    def draft_state(self):
        stage_draft = self.env['library.checkout.stage'].search([('state', '=', 'draft')])
        for chk in self:
            chk.stage_id = stage_draft
            for book in chk.checkout_book_line_ids:
                book.meta_book_id.state = 'available'
                book.meta_book_id.checkout_id = ''
            for pro in chk.checkout_project_line_ids:
                pro.meta_project_id.state = 'available'
                pro.meta_project_id.checkout_id = ''
            chk.borrow_date = ''
            chk.name_seq = 'New'

    def running_state(self):
        chk_mg_new = self.env['library.checkout.magazine.newspaper']
        stage_running = self.env['library.checkout.stage'].search([('state', '=', 'running')])
        for chk in self:
            if not chk.checkout_project_line_ids and not chk.checkout_book_line_ids:
                raise ValidationError('Choose Document!')
            if chk_mg_new.search([('card_id', '=', chk.card_id.id),
                                  ('state', '=', 'running')]):
                raise ValidationError('Checkout magazine newspaper exists. Please return the document to continue!')
            if chk.name_seq == 'New':
                chk.name_seq = self.env['ir.sequence'].next_by_code('library.checkout.sequence') or _('New')
            for book in chk.checkout_book_line_ids:
                print(book)
                print(book.meta_book_id.state)
                if book.meta_book_id.state == 'not_available':
                    raise ValidationError('The book : %s has been borrowed' % (book.book_id.name))
                else:
                    book.meta_book_id.state = 'not_available'
                    book.meta_book_id.checkout_id = chk.id
            for pro in chk.checkout_project_line_ids:
                print(pro)
                print(pro.meta_project_id.state)
                if pro.meta_project_id.state == 'not_available':
                    raise ValidationError('The project : %s has been borrowed' % (pro.project_id.name))
                else:
                    pro.meta_project_id.state = 'not_available'
                    pro.meta_project_id.checkout_id = chk.id
            chk.stage_id = stage_running
            chk.borrow_date = fields.Datetime.now()

    def done_state(self):
        stage_done = self.env['library.checkout.stage'].search([('state', '=', 'done')])
        for chk in self:
            for book in chk.checkout_book_line_ids:
                if book.state == 'not_available':
                    raise ValidationError('you need to return book : %s' % (book.book_id.name))
            for pro in chk.checkout_project_line_ids:
                if pro.state == 'not_available':
                    raise ValidationError('you need to return project : %s' % (pro.project_id.name))
            chk.stage_id = stage_done

    @api.multi
    def fined_state(self):
        stage_fined = self.env['library.checkout.stage'].search([('state', '=', 'fined')])
        for chk in self:
            chk.stage_id = stage_fined
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'checkout.book.project',
                'res_id': chk.id,
                'context': context
            }

    """xoá bản ghi"""
    def unlink(self):
        for chk in self:
            if chk.state != 'draft':
                raise ValidationError('Cannot delete record when state is not draft!')
            for r in chk.checkout_book_line_ids:
                r.unlink()
        return super(CheckoutBookProject, self).unlink()

    @api.constrains('num_document', 'checkout_book_line_ids', 'checkout_project_line_ids')
    def _constrains_limit_book_syllabus(self):
        for chk in self:
            chk_book = len(chk.checkout_book_line_ids) if len(chk.checkout_book_line_ids) else 0
            chk_pro = len(chk.checkout_project_line_ids) if len(chk.checkout_project_line_ids) else 0
            if not chk_book and not chk_pro:
                raise ValidationError('Please select document for checkout!')
            if (chk_book + chk_pro) > chk.num_document:
                raise ValidationError('Cannot borrow more than %s document' % (chk.num_document))


class CheckoutBookLine(models.Model):
    _name = 'checkout.book.line'
    _description = 'Checkout Book Line'

    checkout_id = fields.Many2one('checkout.book.project', string='Checkout ID')
    book_id = fields.Many2one('library.book', 'Book Title')
    meta_book_id = fields.Many2one('meta.books',
                                   string='Meta Book')
    category = fields.Many2one('library.category', related='book_id.category', track_visibility='always')
    status_document = fields.Text('Description', related='meta_book_id.description', store=True,
                                  track_visibility='always')
    state_chk = fields.Selection(related='checkout_id.state', string='State Checkout')
    state = fields.Selection(related='meta_book_id.state', store=True)
    is_lost = fields.Boolean(related='meta_book_id.is_lost')

    def done_state(self):
        for book in self:
            if book.meta_book_id.state == 'not_available':
                book.meta_book_id.state = 'available'
                book.meta_book_id.checkout_id = ''
            if book.meta_book_id.is_lost:
                book.meta_book_id.is_lost = False

    def lost_state(self):
        for book in self:
            if book.meta_book_id.state == 'not_available':
                book.meta_book_id.is_lost = True
                book.checkout_id.price += book.book_id.price
            if not book.checkout_id.note:
                book.checkout_id.note = 'Lost Book: %s - %s' % (book.book_id.name, book.meta_book_id.name_seq)
            else:
                book.checkout_id.note += 'Lost Book: %s - %s' % (book.book_id.name, book.meta_book_id.name_seq)

    @api.onchange('book_id')
    def _onchange_book_id(self):
        self.meta_book_id = ''
        return {'domain': {'meta_book_id': [('state', '=', 'available'),
                                                ('book_id', '=', self.book_id.id)]}}

    """constrains cannot borrow same book in checkout"""
    @api.constrains('book_id')
    def _constrains_book_ids(self):
        for r in self:
            if self.search_count([('checkout_id', '=', r.checkout_id.id),
                                  ('book_id', '=', r.book_id.id)]) > 1:
                raise ValidationError('Cannot borrow same book on checkout!')
            if r.book_id and not r.meta_book_id:
                raise ValidationError('Select meta book for %s' % (r.book_id.name))

    def unlink(self):
        for book in self:
            if book.state == 'not_available':
                raise ValidationError('cannot delete!')
        return super(CheckoutBookLine, self).unlink()


class CheckoutProjectLine(models.Model):
    _name = 'checkout.project.line'
    _description = 'Checkout Project Line'

    checkout_id = fields.Many2one('checkout.book.project', string='Checkout ID')
    project_id = fields.Many2one('document.project', 'Project')
    meta_project_id = fields.Many2one('meta.projects',
                                      string='Meta Project', required=True)
    status_document = fields.Text('Description', related='meta_project_id.description', store=True,
                                  track_visibility='always')
    state = fields.Selection(related='meta_project_id.state', store=True)

    def done_state(self):
        for pro in self:
            pro.meta_project_id.state = 'available'
            pro.meta_project_id.checkout_id = ''

    @api.onchange('project_id')
    def _onchange_book_id(self):
        self.meta_project_id = ''
        return {'domain': {'meta_project_id': [('state', '=', 'available'),
                                                   ('project_id', '=', self.project_id.id)]}}

    """constrains cannot borrow same project in checkout"""
    @api.constrains('project_id')
    def _constrains_project_ids(self):
        for r in self:
            if self.search_count([('checkout_id', '=', r.checkout_id.id),
                                  ('project_id', '=', r.project_id.id)]) > 1:
                print(self.search_count([('checkout_id', '=', r.checkout_id.id),
                                  ('project_id', '=', r.project_id.id)]))
                raise ValidationError('Cannot borrow same project on checkout!')
            if r.project_id and not r.meta_project_id:
                raise ValidationError('Select meta project for %s' % (r.project_id.name))

    def unlink(self):
        for pro in self:
            if pro.state == 'not_available':
                raise ValidationError('cannot delete!')
        return super(CheckoutProjectLine, self).unlink()