from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta as rd
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import pytz
from collections import Counter


class CheckoutBackHome(models.Model):
    _name = 'lib.checkout.back.home'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Checkout Back Home'

    @api.model
    def _default_stage(self):
        return self.env['lib.checkout.stage'].search([], limit=1)

    @api.model
    def _group_expand_stage_id(self, stages, domain, order):
        return stages.search([], order=order)

    name_seq = fields.Char(string="Checkout ID", default=lambda self: _('New'), readonly=True)
    card_id = fields.Many2one('lib.card', string="Card ID",
                              required=True,
                              domain=[('state', '=', 'running'), ('is_penalty', '=', False)])
    state_card = fields.Selection(related='card_id.state', store=True, string='State Card')
    stage_id = fields.Many2one('lib.checkout.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               )
    state = fields.Selection(related='stage_id.state', store=True, string='State')
    gt_name = fields.Char(related='card_id.gt_name', string='The user\'s card', store=True)
    end_date = fields.Date(related='card_id.end_date', string='End Date', store=True)
    type_document = fields.Selection([
        ('book', 'Book'),
        ('project', 'Project'),
    ], string='Type Document', required=True)

    book_id = fields.Many2one('lib.book', 'Name Book')
    meta_book_id = fields.Many2one('lib.meta.books', string='Meta Book')
    project_id = fields.Many2one('lib.document.project', 'Name Project')
    meta_project_id = fields.Many2one('lib.meta.projects', string='Meta Project')
    status_document = fields.Text('Description', compute='_compute_status_document_doc_price', store=True)
    category_doc = fields.Many2one(string='Category', related='book_id.category', store=True)
    doc_price = fields.Monetary("Price Doc", 'currency_id', compute='_compute_status_document_doc_price', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda s: s.env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1))
    penalty_chk_price = fields.Monetary('Penalty Price Checkout', 'currency_id')
    penalty_doc_price = fields.Monetary('Penalty Price Book', 'currency_id')
    penalty_total = fields.Monetary('Penalty Total', 'currency_id', compute="_compute_penalty_total", store=True)
    day_overdue = fields.Integer('Day overdue')
    note = fields.Char('Note')
    document_term = fields.Integer('Document Term (Days)', compute='_compute_status_document_doc_price', store=True)

    user_id = fields.Many2one('res.users', 'Librarian',
                              default=lambda s: s.env.uid,
                              readonly=True)
    user_image = fields.Binary(related='user_id.image', store=True)
    borrow_date = fields.Datetime(string="Borrow date", readonly=True)
    return_date = fields.Date(string="Return Appointment Date")
    actual_return_date = fields.Datetime(string="Actual Return Date")
    priority = fields.Selection(
        [('0', 'Low'),
         ('1', 'Normal'),
         ('2', 'High')],
        'Priority',
        default='0')
    kanban_state = fields.Selection(
        [('normal', 'In Progress'),
         ('overdue', 'Borrow Overdue')],
        'Kanban State',
        default='normal')
    email = fields.Char('Email',related='card_id.email', store=True)
    count_doc = fields.Integer(string="Count Document", compute='_compute_count_chk_bh')
    count_syl = fields.Integer(string="Count Syllabus", compute='_compute_count_chk_bh')
    count_penalty = fields.Integer(string="Count Penalty", compute='_compute_count_chk_bh')
    count_waiting = fields.Integer(string="Count Waiting", compute='_compute_count_chk_bh')

    @api.multi
    def name_get(self):
        res = []
        for chk in self:
            res.append((chk.id, '%s - %s' % (chk.name_seq, chk.gt_name)))
        return res

    @api.onchange('card_id')
    def onchange_card_id(self):
        syll_cate = self.env.ref('do_an_tn.data_category_6').id
        chk_running_syl = self.sudo().search([('card_id', '=', self.card_id.id),
                                              ('state', '=', 'running'),
                                              ('id', 'not in', self.ids),
                                              ('category_doc', '=', syll_cate)])
        chk_running_bk = self.sudo().search([('card_id', '=', self.card_id.id),
                                             ('state', '=', 'running'),
                                             ('id', 'not in', self.ids),
                                             ('category_doc', '!=', syll_cate)])
        if self.card_id :
            if len(chk_running_syl) >= self.card_id.syllabus_limit and len(chk_running_bk) >= self.card_id.book_limit:
                self.card_id = ''
                return {
                    'warning': {
                        'title': _('Card ID'),
                        'message': _('You have borrowed a sufficient number of documents allowed.\nCannot borrow document for this card!'),
                    }
                }
            elif len(chk_running_bk) >= self.card_id.book_limit or len(chk_running_syl) >= self.card_id.syllabus_limit:
                return {
                    'warning': {
                        'title': _('Card ID'),
                        'message': _('Book Limit on card: %s\nSyllabus limit on card: %s\nYou are borrowing %s book(not syllabus) or document and %s syllabus!')
                                     % (self.card_id.book_limit,  self.card_id.syllabus_limit, len(chk_running_bk), len(chk_running_syl)),
                    }
                }

    @api.constrains('book_id', 'meta_book_id', 'project_id', 'meta_project_id')
    def _constrains_doc_meta_doc(self):
        if self.book_id != self.meta_book_id.book_id:
            raise ValidationError(_('Let \'s select meta book again!'))
        elif self.project_id != self.meta_project_id.project_id:
            raise ValidationError(_('Let \'s select meta project again!'))

    @api.onchange('meta_book_id', 'meta_project_id')
    def _onchange_meta_book_id(self):
        if self.book_id:
            return {'domain': {'meta_book_id': [('book_id', '=', self.book_id.id), ('state', '=', 'available')]}}
        elif self.project_id:
            return {'domain': {'meta_project_id': [('project_id', '=', self.project_id.id), ('state', '=', 'available')]}}

    @api.constrains('card_id', 'book_id', 'project_id')
    def _constrains_card_id_book_project(self):
        lib_checkout = self.env['lib.checkout.back.home']
        domain = [('card_id', '=', self.card_id.id),
                  ('state', 'in', ['running', 'draft']),
                  ('book_id', '=', self.book_id.id),
                  ('project_id', '=', self.project_id.id),
                  ('id', 'not in', self.ids)]
        chk_of_card = lib_checkout.sudo().search(domain)
        if chk_of_card:
            raise ValidationError(_('You cannot borrow book to same card more than once!'))

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
                           'message': _('Exceeded deadline for returning books!')
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
                    'message': _('Exceeded term of library card!'),
                }
            }

    @api.constrains('return_date', 'end_date')
    def constrains_return_date_end_date(self):
        for chk in self:
            if chk.return_date and chk.end_date and chk.return_date > chk.end_date:
                raise ValidationError(_('Exceeded term of library card!'))

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
    def _compute_status_document_doc_price(self):
        for chk in self:
            if chk.meta_book_id:
                chk.status_document = chk.meta_book_id.description
                chk.doc_price = chk.book_id.price
                chk.document_term = chk.book_id.book_term
            elif chk.meta_project_id:
                chk.status_document = chk.meta_project_id.description
                chk.doc_price = chk.project_id.price
                chk.document_term = chk.project_id.project_term

    # @api.depends('book_id', 'project_id')
    # def _compute_category_doc(self):
    #     for chk in self:
    #         if chk.book_id:
    #             chk.category_doc = chk.book_id.category.name
    #         elif chk.project_id:
    #             chk.category_doc = chk.project_id.major_id.name

    # def unlink(self):
    #     for chk in self:
    #         if chk.state != 'draft':
    #             raise ValidationError(_('You can not delete checkout when state not is draft!'))
    #     return super(CheckoutBackHome, self).unlink()

    @api.onchange('state')
    def _onchange_state(self):
        if self.state == 'draft':
            self.update({
                'borrow_date': '',
                'return_date': '',
                'actual_return_date': '',
                'day_overdue': '',
                'penalty_doc_price': '',
                'penalty_chk_price': '',
                'penalty_total': '',
                'note': '',
            })
        elif self.state == 'done':
            self.actual_return_date = fields.Datetime.now()
            self.update({
                'day_overdue': '',
                'penalty_doc_price': '',
                'penalty_chk_price': '',
                'penalty_total': '',
                'note': '',
            })
        elif self.state == 'fined':
            self.day_overdue = (fields.Date.today() - self.return_date).days if self.return_date < fields.Date.today() else 0
            self.penalty_chk_price = self.day_overdue * 1000
            self.actual_return_date = fields.Datetime.now()
            self.penalty_doc_price = 0
            self.note = ''
        elif self.state == 'lost':
            self.day_overdue = (fields.Date.today() - self.return_date).days if self.return_date < fields.Date.today() else 0
            self.penalty_chk_price = self.day_overdue * 1000
            self.penalty_doc_price = self.doc_price
            self.actual_return_date = fields.Datetime.now()
        self.kanban_state = 'normal'

    def running_state(self):
        syll_cate = self.env.ref('do_an_tn.data_category_6').id
        state_running = self.env['lib.checkout.stage'].search([('state', '=', 'running')])
        for chk in self:
            chk_running_syl = self.sudo().search([('card_id', '=', chk.card_id.id),
                                           ('state', '=', 'running'),
                                           ('id', 'not in', chk.ids),
                                           ('type_document', '=', 'book'),
                                           ('category_doc', '=', syll_cate)])
            chk_running_bk = self.sudo().search([('card_id', '=', chk.card_id.id),
                                          ('state', '=', 'running'),
                                          ('id', 'not in', chk.ids),
                                          ('category_doc', '!=', syll_cate)])
            if len(chk_running_bk) >= chk.card_id.book_limit and len(chk_running_syl) >= chk.card_id.syllabus_limit:
                raise ValidationError(_('Can not borrow more documents'))
            elif len(chk_running_bk) >= chk.card_id.book_limit:
                if self.category_doc.id != syll_cate:
                    raise ValidationError(_('Unable to borrow more books!'))
            elif len(chk_running_syl) >= chk.card_id.syllabus_limit:
                if self.category_doc.id == syll_cate:
                    raise ValidationError(_('Can not borrow more textbooks!'))
            chk.name_seq = self.env['ir.sequence'].next_by_code('lib.checkout.sequence') or _('New')
            chk.stage_id = state_running
            if chk.book_id:
                if not chk.meta_book_id:
                    raise ValidationError(_('Choose Meta Book!'))
                if chk.meta_book_id.state == 'available':
                    chk.meta_book_id.write({
                        'state': 'not_available',
                        'checkout': str(chk.name_get()[0][1]) + _(' - Back Home'),
                    })
                    chk.book_id._compute_quantity_remaining()
                else:
                    raise ValidationError(_('Book: "%s - %s" have borrowed.' %
                                            (str(self.meta_book_id.name_seq), str(self.meta_book_id.book_id.name))))
            elif chk.project_id:
                if not chk.meta_project_id:
                    raise ValidationError(_('Choose Meta Project!'))
                if chk.meta_project_id.state == 'available':
                    chk.meta_project_id.write({
                        'state': 'not_available',
                        'checkout': str(chk.name_get()[0][1]) + _(' - Back Home'),
                    })
                    chk.project_id._compute_quantity_remaining()
                else:
                    raise ValidationError(_('Project: " %s " have borrowed.' % (str(self.project_id.name))))
            chk.borrow_date = fields.Datetime.now()

    @api.multi
    def draft_state(self):
        stage_draft = self.env['lib.checkout.stage'].search([('state', '=', 'draft')])
        for chk in self:
            chk.stage_id = stage_draft
            chk._onchange_state()
            if chk.book_id and chk.meta_book_id.state == 'not_available':
                chk.meta_book_id.write({
                    'state': 'available',
                    'checkout': '',
                })
                chk.book_id._compute_quantity_remaining()
            elif chk.project_id and chk.meta_project_id.state == 'not_available':
                chk.meta_project_id.write({
                    'state': 'available',
                    'checkout': '',
                })
                chk.project_id._compute_quantity_remaining()

    @api.multi
    def done_state(self):
        Stages = self.env['lib.checkout.stage']
        stage_done = Stages.search([('state', '=', 'done')])
        stage_fined = Stages.search([('state', '=', 'fined')])
        for chk in self:
            if chk.return_date >= fields.Date.today():
                chk.stage_id = stage_done
                chk._onchange_state()
                if chk.book_id and chk.meta_book_id.state == 'not_available':
                    chk.meta_book_id.write({
                        'state': 'available',
                        'checkout': '',
                    })
                    chk.book_id._compute_quantity_remaining()
                elif chk.project_id and chk.meta_project_id.state == 'not_available':
                    chk.meta_project_id.write({
                        'state': 'available',
                        'checkout': '',
                    })
                    chk.project_id._compute_quantity_remaining()
            elif chk.return_date < fields.Date.today():
                chk.stage_id = stage_fined
                chk._onchange_state()
                if chk.book_id and chk.meta_book_id.state == 'not_available':
                    chk.meta_book_id.write({
                        'state': 'available',
                        'checkout': '',
                    })
                    chk.book_id._compute_quantity_remaining()
                elif chk.project_id and chk.meta_project_id.state == 'not_available':
                    chk.meta_project_id.write({
                        'state': 'available',
                        'checkout': '',
                    })
                    chk.project_id._compute_quantity_remaining()

    def fined_state(self):
        stage_fined = self.env['lib.checkout.stage'].search([('state', '=', 'fined')])
        for chk in self:
            chk.stage_id = stage_fined
            chk._onchange_state()
            if chk.book_id and chk.meta_book_id.state == 'not_available':
                chk.meta_book_id.write({
                    'state': 'available',
                    'checkout': '',
                })
                chk.book_id._compute_quantity_remaining()
            elif chk.project_id and chk.meta_project_id.state == 'not_available':
                chk.meta_project_id.write({
                    'state': 'available',
                    'checkout': '',
                })
                chk.project_id._compute_quantity_remaining()
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'lib.checkout.back.home',
                'res_id': chk.id,
                'context': context,
                'target': 'current',
            }

    @api.multi
    def lost_document(self):
        stage_lost = self.env['lib.checkout.stage'].search([('state', '=', 'lost')])
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
                chk.book_id._compute_quantity_remaining()
                chk.note = _('lost document: %s') % (str(chk.meta_book_id.name_seq))
            elif chk.project_id:
                chk.meta_project_id.write(dic)
                chk.project_id._compute_quantity_remaining()
                chk.note = _('lost document: %s') % (str(chk.meta_project_id.name_seq))

    def cancel_state(self):
        Stages = self.env['lib.checkout.stage']
        stage_fined = Stages.search([('state', '=', 'fined')])
        stage_lost = Stages.search([('state', '=', 'lost')])
        stage_done = Stages.search([('state', '=', 'done')])
        for chk in self:
            if chk.stage_id == stage_lost:
                chk.stage_id = stage_fined
                chk._onchange_state()
                if chk.book_id and chk.meta_book_id.state == 'not_available':
                    chk.meta_book_id.write({
                        'state': 'available',
                        'checkout': '',
                        'is_lost': False,
                    })
                    chk.book_id._compute_quantity_remaining()
                elif chk.project_id and chk.meta_project_id.state == 'not_available':
                    chk.meta_project_id.write({
                        'state': 'available',
                        'checkout': '',
                        'is_lost': False,
                    })
                    chk.project_id._compute_quantity_remaining()
                context = dict(self.env.context)
                context['form_view_initial_mode'] = 'edit'
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'lib.checkout.back.home',
                    'res_id': chk.id,
                    'context': context
                }
            if chk.stage_id == stage_fined:
                if self.return_date >= fields.Date.today():
                    chk.stage_id = stage_done
                    chk._onchange_state()
                else:
                    if chk.book_id:
                        chk.meta_book_id.write({
                            'description': chk.status_document
                        })
                    elif chk.project_id:
                        chk.meta_project_id.write({
                            'description': chk.status_document
                        })
                    chk.penalty_doc_price = 0
                    chk.note = ''

    @api.depends('penalty_chk_price', 'penalty_doc_price')
    def _compute_penalty_total(self):
        for chk in self:
            chk.penalty_total = chk.penalty_chk_price + chk.penalty_doc_price

    def _compute_count_chk_bh(self):
        syll_cate = self.env.ref('do_an_tn.data_category_6').id
        for chk in self:
            chk_hb = self.sudo().search([('card_id', '=', chk.card_id.id),
                                         ('state', '=', 'running')])
            chk.count_syl = len(chk_hb.filtered(lambda a: a.category_doc.id == syll_cate))
            chk.count_doc = len(chk_hb) - chk.count_syl
            chk.count_penalty = len(self.sudo().search([('card_id', '=', chk.card_id.id),
                                                        ('state', 'in', ['fined', 'lost'])]))

            chk.count_waiting = self.search_count([('state', '=', 'draft'),
                                                   ('book_id', '=', self.book_id.id),
                                                   ('project_id', '=', self.project_id.id)])

    @api.multi
    def open_chk_document(self):
        syll_cate = self.env.ref('do_an_tn.data_category_6').id
        return {
            'name': _('Checkout Document'),
            'domain': [('card_id', '=', self.card_id.id),
                       ('state', '=', 'running'),
                       ('category_doc', '!=', syll_cate)],
            'view_type': 'form',
            'res_model': 'lib.checkout.back.home',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def open_chk_syllabus(self):
        syll_cate = self.env.ref('do_an_tn.data_category_6').id
        return {
            'name': _('Checkout Syllabus'),
            'domain': [('card_id', '=', self.card_id.id),
                       ('state', '=', 'running'),
                       ('type_document', '=', 'book'),
                       ('category_doc', '=', syll_cate)],
            'view_type': 'form',
            'res_model': 'lib.checkout.back.home',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def open_all_checkout_bh(self):
        return {
            'name': _('All Checkout Back Home'),
            'domain': [('card_id', '=', self.card_id.id),
                       ('state', '=', 'running')],
            'view_type': 'form',
            'res_model': 'lib.checkout.back.home',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def open_all_penalty_checkout(self):
        return {
            'name': _('Penalty Checkout'),
            'domain': [('card_id', '=', self.card_id.id),
                       ('state', 'in', ['fined', 'lost'])],
            'view_type': 'form',
            'res_model': 'lib.checkout.back.home',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def library_chk_bh_check_ret_date(self):
        current_date = datetime.now()
        print('Library checkout back home check return appointment date!')
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        CheckoutBH = self.sudo().search([('state', '=', 'running'),
                                         ('return_date', '<', date_today),
                                         ('kanban_state', '!=', 'overdue')])
        template_id = self.env.ref('do_an_tn.scheduled_send_mail_chk_overdue').id
        template = self.env['mail.template'].browse(template_id)
        for chk in CheckoutBH:
            # template.send_mail(chk.id, force_send=True, raise_exception=True)
            # chk.message_post(_('Send Email for Checkout'))
            chk.kanban_state = 'overdue'

    @api.multi
    def open_checkout_waiting(self):
        return {
            'name': _('Open Checkout Waiting'),
            'domain': [('state', '=', 'draft'),
                       ('book_id', '=', self.book_id.id),
                       ('project_id', '=', self.project_id.id)],
            'view_type': 'form',
            'res_model': 'lib.checkout.back.home',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }






