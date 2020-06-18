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
        print(self.env.context.get('active_id'))
        chk = self.env.context.get('active_id')
        chk_mg_new = self.env['library.checkout.magazine.newspaper'].search([('id', '=', chk)])
        defaults['mgz_new_id'] = chk_mg_new.mgz_new_id.id
        defaults['meta_mgz_new_id'] = chk_mg_new.meta_mgz_new_id.id
        if chk_mg_new.state == 'lost':
            defaults['status_document'] = 'Lost Document'
        else:
            defaults['status_document'] = chk_mg_new.status_document + '. ' + str(chk_mg_new.note)
        return defaults

    @api.multi
    def button_update_description(self):
        print(str(self.status_document))
        self.meta_mgz_new_id.write({'description': self.status_document})
        msg = str(self.meta_mgz_new_id.name_seq) + ' updated by ' + str(self.user_id.name)
        self.mgz_new_id.message_post(body=msg)