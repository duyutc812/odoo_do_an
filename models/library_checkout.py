from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import pytz


class CheckoutMagazineNewspaper(models.Model):
    _name = 'library.checkout.magazine.newspaper'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Checkout Magazine Newspaper'

    @api.model
    def _default_stage(self):
        return self.env['library.checkout.stage'].search([], limit=1)

    @api.model
    def _group_expand_stage_id(self, stages, domain, order):
        return stages.search([], order=order)

    card_id = fields.Many2one('library.card', string="Card No",
                              required=True,
                              domain=[('state', '=', 'running'), ('is_penalty', '=', False)], track_visibility='always')
    gt_name = fields.Char(related='card_id.gt_name', store=True, track_visibility='always')
    stage_id = fields.Many2one('library.checkout.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               track_visibility='always'
                               )
    state = fields.Selection(related='stage_id.state', store=True)
    name_seq = fields.Char(string="Checkout ID", default=lambda self: _('New'), readonly=True)
    borrow_date = fields.Datetime(string='Borrow Date', default=fields.Datetime.now(), track_visibility='always')
    mgz_new_id = fields.Many2one('magazine.newspaper', 'Name Mgz/New', required=True, track_visibility='always')
    meta_mgz_new_id = fields.Many2one('meta.magazinenewspapers',
                                      string='Meta Mgz-New', required=True, track_visibility='always')
    status_document = fields.Text('Description', related="meta_mgz_new_id.description", store=True, track_visibility='always')
    user_id = fields.Many2one('res.users', 'Librarian',
                              default=lambda s: s.env.uid,
                              readonly=True, track_visibility='always')

    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda s: s.env['res.currency'].search([('name', '=', 'VND')], limit=1))
    price = fields.Monetary('Price', 'currency_id')
    note = fields.Char('Note')

    @api.multi
    def running_state(self):
        stage_running = self.env['library.checkout.stage'].search([('state', '=', 'running')])
        for chk_mg_new in self:
            if chk_mg_new.name_seq == 'New':
                chk_mg_new.name_seq = self.env['ir.sequence'].next_by_code('library.checkout.sequence') or _('New')
            if chk_mg_new.meta_mgz_new_id.state == 'available':
                chk_mg_new.stage_id = stage_running
                chk_mg_new.meta_mgz_new_id.state = 'not_available'
                chk_mg_new.mgz_new_id.remaining -= 1
                chk_mg_new.meta_mgz_new_id.chk_mg_new_id = chk_mg_new.id
            else:
                raise ValidationError('Magazine/Newspaper have borrowed.')

    @api.multi
    def draft_state(self):
        stage_draft = self.env['library.checkout.stage'].search([('state', '=', 'draft')])
        for chk_mg_new in self:
            chk_mg_new.stage_id = stage_draft
            if chk_mg_new.meta_mgz_new_id.state == 'not_available':
                chk_mg_new.meta_mgz_new_id.state = 'available'
                chk_mg_new.mgz_new_id.remaining += 1
                chk_mg_new.meta_mgz_new_id.chk_mg_new_id = ''
            chk_mg_new.price = 0
            chk_mg_new.note = ''

    @api.multi
    def done_state(self):
        stage_done = self.env['library.checkout.stage'].search([('state', '=', 'done')])
        for chk_mg_new in self:
            chk_mg_new.stage_id = stage_done
            chk_mg_new.meta_mgz_new_id.state = 'available'
            chk_mg_new.mgz_new_id.remaining += 1
            chk_mg_new.meta_mgz_new_id.chk_mg_new_id = ''

    @api.multi
    def fined_state(self):
        stage_fined = self.env['library.checkout.stage'].search([('state', '=', 'fined')])
        for chk_mg_new in self:
            chk_mg_new.stage_id = stage_fined
            chk_mg_new.meta_mgz_new_id.state = 'available'
            chk_mg_new.mgz_new_id.remaining += 1
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'library.checkout.magazine.newspaper',
                'res_id': chk_mg_new.id,
                'context': context
            }

    @api.multi
    def lost_document(self):
        stage_fined = self.env['library.checkout.stage'].search([('state', '=', 'fined')])
        for chk_mg_new in self:
            chk_mg_new.stage_id = stage_fined
            chk_mg_new.price = chk_mg_new.mgz_new_id.price
            chk_mg_new.note = 'Lost Document'

    @api.constrains('card_id', 'mgz_new_id')
    def _constrains_card_id_book(self):
        domain = [('card_id', '=', self.card_id.id),
                  ('state', 'not in', ('done', 'fined')),
                  ('id', 'not in', self.ids)]
        another_chk = self.search(domain)
        print(another_chk)
        if another_chk:
            raise ValidationError('You cannot borrow Magazine or Newspaper to same card more than once!')

    @api.multi
    def name_get(self):
        res = []
        for chk_mg_new in self:
            res.append((chk_mg_new.id, '%s - %s' % (chk_mg_new.name_seq, chk_mg_new.gt_name)))
        return res

    @api.onchange('mgz_new_id')
    def _onchange_mgz_new_id(self):
        for chk in self:
            chk.meta_mgz_new_id = ''
            # print(chk.mgz_new_id)
            return {'domain': {'meta_mgz_new_id': [('state', '=', 'available'),
                                                   ('mgz_new_id', '=', chk.mgz_new_id.id)]}}

    def unlink(self):
        for chk in self:
            if chk.state == 'running' or chk.state == 'fined':
                raise ValidationError('You can not delete checkout when state is borrowed, fined')

        return super(CheckoutMagazineNewspaper, self).unlink()





