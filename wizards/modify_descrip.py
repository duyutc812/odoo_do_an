from odoo import api, fields, models


class ModifyDescriptionDoc(models.TransientModel):
    _name = 'modify.description.doc'
    _description = 'Modify Description'

    book_id = fields.Many2one('library.book', 'Name Book', readonly=True)
    meta_book_id = fields.Many2one('meta.books', 'Meta Book', readonly=True)
    mgz_new_id = fields.Many2one('magazine.newspaper', 'Name Mgz/New', readonly=True)
    meta_mgz_new_id = fields.Many2one('meta.magazinenewspapers', 'Meta Mgz-New', readonly=True)
    project_id = fields.Many2one('document.project', 'Name Project', readonly=True)
    meta_project_id = fields.Many2one('meta.projects', 'Meta Project', readonly=True)
    status_document = fields.Text('Description', track_visibility='always')
    user_id = fields.Many2one('res.users', 'Librarian',
                              default=lambda s: s.env.uid,
                              readonly=True)

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        # print(defaults)
        # {}

        chk = self.env['library.checkout.at.lib'].search([('id', '=', self.env.context.get('active_id'))])
        if chk.book_id:
            defaults['book_id'] = chk.book_id.id
            defaults['meta_book_id'] = chk.meta_book_id.id
        elif chk.mgz_new_id:
            defaults['mgz_new_id'] = chk.mgz_new_id.id
            defaults['meta_mgz_new_id'] = chk.meta_mgz_new_id.id
        elif chk.project_id:
            defaults['project_id'] = chk.project_id.id
            defaults['meta_project_id'] = chk.meta_project_id.id
        defaults['status_document'] = chk.status_document + '. ' + (str(chk.note) if chk.note else '')
        return defaults

    @api.multi
    def button_update_description(self):
        if self.book_id:
            self.meta_book_id.write({'description': self.status_document})
            msg = str(self.meta_book_id.name_seq) + ' updated by ' + str(self.user_id.name)
            self.book_id.message_post(body=msg)
        elif self.mgz_new_id:
            self.meta_mgz_new_id.write({'description': self.status_document})
            msg = str(self.meta_mgz_new_id.name_seq) + ' updated by ' + str(self.user_id.name)
            self.mgz_new_id.message_post(body=msg)
        elif self.project_id:
            self.meta_project_id.write({'description': self.status_document})
            msg = str(self.meta_project_id.name_seq) + ' updated by ' + str(self.user_id.name)
            self.project_id.message_post(body=msg)


# class ModifyDescriptionBook(models.TransientModel):
#     _name = 'modify.description.book'
#     _description = 'Modify Description Book'
#
#     book_id = fields.Many2one('library.book', 'Book Title', readonly=True)
#     meta_book_ids = fields.Many2one('meta.books', 'Meta Book', readonly=True)
#     status_document = fields.Text('Description', track_visibility='always')
#     user_id = fields.Many2one('res.users', 'Librarian',
#                               default=lambda s: s.env.uid,
#                               readonly=True)
#
#     @api.model
#     def default_get(self, field_names):
#         defaults = super().default_get(field_names)
#         # print(defaults)
#         # {}
#         print(self.env.context.get('active_id'))
#         chk = self.env['checkout.book.line'].search([('id', '=', self.env.context.get('active_id'))])
#         defaults['book_id'] = chk.book_id.id
#         defaults['meta_book_ids'] = chk.meta_book_id.id
#         defaults['status_document'] = chk.status_document
#         return defaults
#
#     @api.multi
#     def button_update_description(self):
#         print(str(self.status_document))
#         self.meta_book_ids.write({'description': self.status_document})
#         msg = str(self.meta_book_ids.name_seq) + ' updated by ' + str(self.user_id.name)
#         self.book_id.message_post(body=msg)
#
#
# class ModifyDescriptionProject(models.TransientModel):
#     _name = 'modify.description.project'
#     _description = 'Modify Description Project'
#
#     project_id = fields.Many2one('document.project', 'Project Name', readonly=True)
#     meta_project_ids = fields.Many2one('meta.projects', 'Meta Project', readonly=True)
#     status_document = fields.Text('Description', track_visibility='always')
#     user_id = fields.Many2one('res.users', 'Librarian',
#                               default=lambda s: s.env.uid,
#                               readonly=True)
#
#     @api.model
#     def default_get(self, field_names):
#         defaults = super().default_get(field_names)
#         # print(defaults)
#         # {}
#         print(self.env.context.get('active_id'))
#         chk = self.env['checkout.project.line'].search([('id', '=', self.env.context.get('active_id'))])
#         defaults['project_id'] = chk.project_id.id
#         defaults['meta_project_ids'] = chk.meta_project_id.id
#         #
#         # if chk_mg_new.state == 'lost':
#         #     defaults['status_document'] = 'Lost Document'
#         # else:
#         #     defaults['status_document'] = chk_mg_new.status_document + '. ' + str(chk_mg_new.note)
#         defaults['status_document'] = chk.status_document
#         return defaults
#
#     @api.multi
#     def button_update_description(self):
#         print(str(self.status_document))
#         self.meta_project_ids.write({'description': self.status_document})
#         msg = str(self.meta_project_ids.name_seq) + ' updated by ' + str(self.user_id.name)
#         self.project_id.message_post(body=msg)


