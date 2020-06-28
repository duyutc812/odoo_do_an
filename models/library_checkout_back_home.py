from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta as rd
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import pytz


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

    card_id = fields.Many2one('library.card', string="Card ID",
                              required=True,
                              domain=[('state', '=', 'running'), ('is_penalty', '=', False)])
    state_card = fields.Selection(related='card_id.state', store=True)
    user_id = fields.Many2one('res.users', 'Librarian',
                              default=lambda s: s.env.uid,
                              readonly=True)
    borrow_date = fields.Datetime(string="Borrow date", readonly=True)
    name_seq = fields.Char(string="Checkout ID", default=lambda self: _('New'), readonly=True)

    # limit_book_card = fields.Integer(related='card_id.book_limit', string='Book limit on card')
    gt_name = fields.Char(related='card_id.gt_name', string='The user\'s card')
    end_date = fields.Date(related='card_id.end_date', string='End Date')
    type_document = fields.Selection([
        ('book', 'Book'),
        ('project', 'Project'),
    ], string='Type Document', required=True)

    book_id = fields.Many2one('library.book', 'Name Book')
    meta_book_id = fields.Many2one('meta.books', string='Meta Book')
    project_id = fields.Many2one('document.project', 'Name Project')
    meta_project_id = fields.Many2one('meta.projects', string='Meta Project')
    status_document = fields.Text('Description', compute='_compute_status_document_price_doc', store=True)
    category_doc = fields.Char(string='Category', compute='_compute_category_doc', store=True)
    price_doc = fields.Monetary("Price Doc", 'currency_id', compute='_compute_status_document_price_doc', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda s: s.env['res.currency'].search([('name', '=', 'VND')], limit=1))
    price_penalty_chk = fields.Monetary('Penalty Price Checkout', 'currency_id')
    price_penalty_doc = fields.Monetary('Penalty Price Book', 'currency_id')
    price_total = fields.Monetary('Penalty Total', 'currency_id', compute="_compute_price_total", store=True)
    day_overdue = fields.Integer('Day overdue')
    note = fields.Char('Note')
    document_term = fields.Integer('Document Term (Days)', compute='_compute_status_document_price_doc', store=True)
    return_date = fields.Date(string="Return Appointment Date")
    actual_return_date = fields.Datetime(string="Actual Return Date")
    color = fields.Integer('Color Index')
    priority = fields.Selection(
        [('0', 'Low'),
         ('1', 'Normal'),
         ('2', 'High')],
        'Priority',
        default='0')
    kanban_state = fields.Selection(
        [('normal', 'Draft'),
         ('blocked', 'Blocked'),
         ('done', 'Borrowed')],
        'Kanban State',
        default='normal')

    @api.multi
    def name_get(self):
        res = []
        for chk in self:
            res.append((chk.id, '%s - %s' % (chk.name_seq, chk.gt_name)))
        return res

    @api.onchange('type_document')
    def onchange_type_document(self):
        if self.type_document == 'project':
            self.book_id = ''
            self.meta_book_id = ''
        elif self.type_document == 'book':
            self.project_id = ''
            self.meta_project_id = ''

    @api.onchange('return_date')
    def _onchange_return_date(self):
        current_date = datetime.now()
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        if self.return_date and self.document_term and (self.return_date > (date_today + rd(days=self.document_term)).date()):
            self.return_date = ''
            return {
                       'warning': {
                           'title': _('Duration Borrow Document'),
                           'message': _('Quá hạn mượn sách!')
                       }
                   }
        # if self.return_date and self.return_date < date_today.date():
        #     self.return_date = ''
        #     return {
        #                'warning': {
        #                    'title': _('Duration Borrow Document'),
        #                    'message': _('Ngày hẹn trả phải lớn hơn ngày hiện tại!'),
        #                }
        #            }
        if self.return_date and self.end_date and self.return_date > self.end_date:
            self.return_date = ''
            return {
                'warning': {
                    'title': _('Card ID'),
                    'message': _('quá thời hạn thẻ !'),
                }
            }

    @api.constrains('return_date', 'end_date')
    def constrains_return_date_end_date(self):
        for chk in self:
            if chk.return_date and chk.end_date and chk.return_date > chk.end_date:
                raise ValidationError(_('quá hạn thẻ!'))

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
                chk.document_term = chk.book_id.book_term
            elif chk.meta_project_id:
                chk.status_document = chk.meta_project_id.description
                chk.price_doc = chk.project_id.price
                chk.document_term = chk.project_id.project_term

    @api.depends('book_id', 'project_id')
    def _compute_category_doc(self):
        for chk in self:
            if chk.book_id:
                chk.category_doc = chk.book_id.category.name
            elif chk.project_id:
                chk.category_doc = chk.project_id.major.name

    def unlink(self):
        for chk in self:
            if chk.state != 'draft':
                raise ValidationError(_('You can not delete checkout when state not is draft!'))
        return super(CheckoutBackHome, self).unlink()

    @api.onchange('state')
    def _onchange_state(self):
        if self.state == 'draft':
            self.borrow_date = ''
            self.return_date = ''
            self.actual_return_date = ''
            self.day_overdue = ''
            self.price_penalty_doc = ''
            self.price_penalty_chk = ''
            self.price_total = ''
            self.note = ''
        elif self.state == 'fined':
            self.day_overdue = (fields.Date.today() - self.return_date).days
            self.price_penalty_chk = self.day_overdue * 10000
        elif self.state == 'cancel':
            self.price_penalty_doc = 0


    @api.multi
    def draft_state(self):
        stage_draft = self.env['library.checkout.stage'].search([('state', '=', 'draft')])
        for chk in self:
            chk.stage_id = stage_draft
            chk._onchange_state()
            chk.kanban_state = 'normal'
            if chk.book_id and chk.meta_book_id.state == 'not_available':
                chk.meta_book_id.write({
                    'state': 'available',
                    'checkout': '',
                })
            elif chk.project_id and chk.meta_project_id.state == 'not_available':
                chk.meta_project_id.write({
                    'state': 'available',
                    'checkout': '',
                })

    def running_state(self):
        state_running = self.env['library.checkout.stage'].search([('state', '=', 'running')])
        for chk in self:
            chk.name_seq = self.env['ir.sequence'].next_by_code('library.checkout.sequence') or _('New')
            chk.stage_id = state_running
            chk.kanban_state = 'done'
            if chk.book_id:
                if chk.meta_book_id.state == 'available':
                    chk.meta_book_id.write({
                        'state': 'not_available',
                        'checkout': str(chk.name_get()[0][1]) + _(' - Back Home'),
                    })
                else:
                    raise ValidationError(_('Book: "%s - %s" have borrowed.' %
                                            (str(self.meta_book_id.name_seq), str(self.meta_book_id.book_id.name))))
            elif chk.project_id:
                if chk.meta_project_id.state == 'available':
                    chk.meta_project_id.write({
                        'state': 'not_available',
                        'checkout': str(chk.name_get()[0][1]) + _(' - Back Home'),
                    })
                else:
                    raise ValidationError(_('Project: " %s " have borrowed.' % (str(self.project_id.name))))
            chk.borrow_date = fields.Datetime.now()

    @api.multi
    def done_state(self):
        Stages = self.env['library.checkout.stage']
        stage_done = Stages.search([('state', '=', 'done')])
        stage_fined = Stages.search([('state', '=', 'fined')])
        for chk in self:
            if chk.return_date >= fields.Date.today():
                chk.stage_id = stage_done
                chk.kanban_state = 'normal'
                if chk.book_id and chk.meta_book_id.state == 'not_available':
                    chk.meta_book_id.write({
                        'state': 'available',
                        'checkout': '',
                    })
                elif chk.project_id and chk.meta_project_id.state == 'not_available':
                    chk.meta_project_id.write({
                        'state': 'available',
                        'checkout': '',
                    })
            elif chk.return_date < fields.Date.today():
                chk.fined_state()
            chk.actual_return_date = fields.Datetime.now()

    def fined_state(self):
        stage_fined = self.env['library.checkout.stage'].search([('state', '=', 'fined')])
        for chk in self:
            chk.stage_id = stage_fined
            chk._onchange_state()
            if chk.book_id and chk.meta_book_id.state == 'not_available':
                chk.meta_book_id.write({
                    'state': 'available',
                    'checkout': '',
                })
            elif chk.project_id and chk.meta_project_id.state == 'not_available':
                chk.meta_project_id.write({
                    'state': 'available',
                    'checkout': '',
                })
            chk.actual_return_date = fields.Datetime.now()
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'library.checkout.back.home',
                'res_id': chk.id,
                'context': context
            }

    @api.multi
    def lost_document(self):
        stage_lost = self.env['library.checkout.stage'].search([('state', '=', 'lost')])
        for chk in self:
            chk.stage_id = stage_lost
            dic = {
                    'is_lost': True,
                    'checkout': str(chk.name_get()[0][1]) + _(' - At lib'),
                    'state': 'not_available',
                }
            if chk.book_id:
                chk.meta_book_id.write(dic)
            elif chk.project_id:
                chk.meta_project_id.write(dic)
            chk.actual_return_date = fields.Datetime.now()
            chk.price_penalty_doc = chk.price_doc
            chk.note = 'lost magazine or newspaper'

    def cancel_state(self):
        stage_cancel = self.env['library.checkout.stage'].search([('state', '=', 'cancel')])
        for chk in self:
            chk.stage_id = stage_cancel
            chk._onchange_state()
            dic = {
                    'state': 'available',
                    'checkout': '',
                    'is_lost': False,
                    'description': chk.status_document,
                }
            if chk.book_id:
                chk.meta_book_id.write(dic)
            elif chk.project_id:
                chk.meta_project_id.write(dic)
            chk.actual_return_date = fields.Datetime.now()

    @api.depends('price_penalty_chk', 'price_penalty_doc')
    def _compute_price_total(self):
        for chk in self:
            chk.price_total = chk.price_penalty_chk + chk.price_penalty_doc






