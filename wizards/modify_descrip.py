from odoo import api, fields, models


class ModifyDescription(models.TransientModel):
    _name = 'modify.description'
    _description = 'Modify Description'

    mgz_new_id = fields.Many2one('magazine.newspaper', 'Name Mgz/New', readonly=True)
    meta_mgz_new_id = fields.Many2one('meta.magazinenewspapers',
                                      string='Meta Mgz-New', readonly=True)
    status_document = fields.Text('Description', track_visibility='always')
    user_id = fields.Many2one('res.users', 'Librarian',
                              default=lambda s: s.env.uid,
                              readonly=True)

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        # print(defaults)
        # {}
        chk = self.env.context.get('active_ids')
        chk_mg_new = self.env['library.checkout.magazine.newspaper'].search([('id', '=', chk[0])])
        defaults['mgz_new_id'] = chk_mg_new.mgz_new_id.id
        defaults['meta_mgz_new_id'] = chk_mg_new.meta_mgz_new_id.id
        return defaults

    @api.multi
    def button_update_description(self):
        self.meta_mgz_new_id.write({'description': self.status_document})
        msg = str(self.meta_mgz_new_id.name_seq) + ' updated by ' + str(self.user_id.name)
        self.mgz_new_id.message_post(body=msg)