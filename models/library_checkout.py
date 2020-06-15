from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import pytz


class CheckoutMagazineNewspaper(models.Model):
    _name = 'library.checkout.magazine.newspaper'
    _description = 'Checkout Magazine Newspaper'

    @api.model
    def _default_stage(self):
        return self.env['library.checkout.stage'].search([], limit=1)

    @api.model
    def _group_expand_stage_id(self, stages, domain, order):
        return stages.search([], order=order)

    card_id = fields.Many2one('library.card', string="Card No",
                              required=True,
                              domain=[('state', '=', 'running')])
    gt_name = fields.Char(related='card_id.gt_name', store=True)
    stage_id = fields.Many2one('library.checkout.stage',
                               default=_default_stage,
                               group_expand='_group_expand_stage_id',
                               )
    state = fields.Selection(related='stage_id.state', store=True)
    name_seq = fields.Char(string="Checkout ID", default=lambda self: _('New'), readonly=True)
    borrow_date = fields.Date(string='Borrow Date', default=fields.Date.today())
    mgz_new_id = fields.Many2one('magazine.newspaper', 'Name Mgz/New')
    meta_mgz_new_id = fields.Many2one('meta.magazinenewspapers',
                                      string='Meta Mgz-New')
    status_document = fields.Text('Description', related="meta_mgz_new_id.description", store=True)
    user_id = fields.Many2one('res.users', 'Librarian',
                              default=lambda s: s.env.uid,
                              readonly=True)

    @api.multi
    def running_state(self):
        stage_running = self.env['library.checkout.stage'].search([('state', '=', 'running')])
        for chk_mg_new in self:
            if chk_mg_new.name_seq == 'New':
                chk_mg_new.name_seq = self.env['ir.sequence'].next_by_code('library.checkout.sequence') or _('New')
            chk_mg_new.stage_id = stage_running

    @api.multi
    def draft_state(self):
        stage_draft = self.env['library.checkout.stage'].search([('state', '=', 'draft')])
        for chk_mg_new in self:
            chk_mg_new.stage_id = stage_draft

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
            print(chk.mgz_new_id)
            return {'domain': {'meta_mgz_new_id': [('state', '=', 'available'),
                                                   ('mgz_new_id', '=', chk.mgz_new_id.id)]}}






