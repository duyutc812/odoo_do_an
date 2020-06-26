from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta as rd
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
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
    start_date = fields.Date(related='card_id.start_date', string='Start date')
    end_date = fields.Date(related='card_id.end_date', string='End Date')
    book_limit_card = fields.Integer(related='card_id.book_limit', store=True)
    limit_syllabus_card = fields.Integer(related='card_id.limit_syllabus', store=True)
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
    price_penalty = fields.Monetary('Penalty Price', 'currency_id')
    note = fields.Char('Note')
    document_term = fields.Integer('Document Term (Days)', compute='_compute_status_document_price_doc', store=True)
    return_date = fields.Date(string="Return Appointment Date")
    actual_return_date = fields.Date(string="Actual Return Date")
    color = fields.Integer('Color Index')
    priority = fields.Selection(
        [('0', 'Low'),
         ('1', 'Normal'),
         ('2', 'High')],
        'Priority',
        default='0')
    kanban_state = fields.Selection(
        [('normal', 'In Progress'),
         ('blocked', 'Blocked'),
         ('done', 'Ready for next stage')],
        'Kanban State',
        default='normal')

    # @api.onchange('card_id')
    # def onchange_member_id(self):
    #     today = fields.Date.today()
    #     if self.borrow_date != today:
    #         self.borrow_date = fields.Datetime.now()
    #         return {
    #             'warning': {
    #                 'title': 'Changed Request Date',
    #                 'message': 'Request date changed to today.'
    #             }
    #         }

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
        if self.return_date and self.document_term and self.return_date > \
                (date_today + rd(days=self.document_term)).date():
            self.return_date = ''
            return {
                       'warning': {
                           'title': 'Duration Borrow Document',
                           'message': 'Quá hạn mượn sách'
                       }
                   }
        if self.return_date < date_today.date():
            return {
                       'warning': {
                           'title': 'Duration Borrow Document',
                           'message': 'Ngày hẹn trả phải lớn hơn ngày hiện tại!'
                       }
                   }

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

    @api.multi
    def name_get(self):
        res = []
        for chk in self:
            res.append((chk.id, '%s - %s' % (chk.name_seq, chk.gt_name)))
        return res

    def unlink(self):
        for chk in self:
            if chk.state != 'draft':
                raise ValidationError('You can not delete checkout when state not is draft!')
        return super(CheckoutBackHome, self).unlink()

    def running_state(self):
        state_running = self.env['library.checkout.stage'].search([('state', '=', 'running')])
        for chk in self:
            chk.name_seq = self.env['ir.sequence'].next_by_code('library.checkout.sequence') or _('New')
            chk.stage_id = state_running
            if chk.book_id:
                if chk.meta_book_id.state == 'available':
                    chk.meta_book_id.state = 'not_available'
                    chk.meta_book_id.checkout = str(chk.name_get()[0][1]) + ' - Back Home'
                else:
                    raise ValidationError('Book: "%s - %s" have borrowed.' %
                                          (self.meta_book_id.name_seq, self.meta_book_id.book_id.name))
            elif chk.project_id:
                if chk.meta_project_id.state == 'available':
                    chk.meta_project_id.state = 'not_available'
                    chk.meta_project_id.checkout = str(chk.name_get()[0][1]) + ' - Back Home'
                else:
                    raise ValidationError('Project: " %s " have borrowed.' % (self.project_id.name))
            chk.borrow_date = fields.Datetime.now()

    @api.multi
    def draft_state(self):
        stage_draft = self.env['library.checkout.stage'].search([('state', '=', 'draft')])
        for chk in self:
            chk.stage_id = stage_draft
            if chk.book_id and chk.meta_book_id.state == 'not_available':
                chk.meta_book_id.state = 'available'
                chk.meta_book_id.checkout = ''
            elif chk.mgz_new_id and chk.meta_mgz_new_id.state == 'not_available':
                chk.meta_mgz_new_id.state = 'available'
                chk.meta_mgz_new_id.checkout = ''
            elif chk.project_id and chk.meta_project_id.state == 'not_available':
                chk.meta_project_id.state = 'available'
                chk.meta_project_id.checkout = ''
            chk.borrow_date = ''

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
