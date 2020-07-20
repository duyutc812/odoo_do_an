from odoo import api, fields, models, _


class ModifyDescriptionDoc(models.TransientModel):
    _name = 'modify.description.doc'
    _description = 'Thay đổi tình trạng tài liệu trên phiếu mượn tại thư viện'

    book_id = fields.Many2one('lib.book', 'Tiêu đề sách', readonly=True)
    meta_book_id = fields.Many2one('lib.meta.books', 'Meta Sách', readonly=True)
    mgz_new_id = fields.Many2one('lib.magazine.newspaper', 'Tạp chí - báo', readonly=True)
    meta_mgz_new_id = fields.Many2one('lib.meta.magazinenewspapers', 'Meta tạp chí - báo', readonly=True)
    project_id = fields.Many2one('lib.document.project', 'Đồ án - luận văn', readonly=True)
    meta_project_id = fields.Many2one('lib.meta.projects', 'Meta đồ án - luận văn', readonly=True)
    status_document = fields.Text('Tình trạng', track_visibility='always')
    user_id = fields.Many2one('res.users', 'Nhân viên thư viện',
                              default=lambda s: s.env.uid,
                              readonly=True)

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        # print(defaults)
        # {}
        chk = self.env['lib.checkout.at.lib'].sudo().search([('id', '=', self.env.context.get('active_id'))])
        if chk.book_id:
            defaults['book_id'] = chk.book_id.id
            defaults['meta_book_id'] = chk.meta_book_id.id
        elif chk.mgz_new_id:
            defaults['mgz_new_id'] = chk.mgz_new_id.id
            defaults['meta_mgz_new_id'] = chk.meta_mgz_new_id.id
        elif chk.project_id:
            defaults['project_id'] = chk.project_id.id
            defaults['meta_project_id'] = chk.meta_project_id.id
        defaults['status_document'] = (chk.status_document if chk.status_document else '') + '. ' + (str(chk.note) if chk.note else '')
        return defaults

    @api.multi
    def button_update_description(self):
        if self.book_id:
            self.meta_book_id.write({'description': self.status_document})
            self.book_id.message_post(_('%s đã được cập nhật bởi %s' % (str(self.meta_book_id.name_seq), str(self.user_id.name))))
        elif self.mgz_new_id:
            self.meta_mgz_new_id.write({'description': self.status_document})
            self.mgz_new_id.message_post(_('%s đã được cập nhật bởi %s' % (str(self.meta_mgz_new_id.name_seq), str(self.user_id.name))))
        elif self.project_id:
            self.meta_project_id.write({'description': self.status_document})
            self.project_id.message_post(_('%s đã được cập nhật bởi %s' % (str(self.meta_project_id.name_seq), str(self.user_id.name))))


class ModifyDescriptionDocCHKBH(models.TransientModel):
    _name = 'modify.description.doc.chk.bh'
    _description = 'Thay đổi tình trạng tài liệu trên phiếu mượn về'

    book_id = fields.Many2one('lib.book', 'Tiêu đề sách', readonly=True)
    meta_book_id = fields.Many2one('lib.meta.books', 'Meta Sách', readonly=True)
    project_id = fields.Many2one('lib.document.project', 'Đồ án - luận văn', readonly=True)
    meta_project_id = fields.Many2one('lib.meta.projects', 'Meta đồ án - luận văn', readonly=True)
    status_document = fields.Text('Description', track_visibility='always')
    user_id = fields.Many2one('res.users', 'Nhân viên thư viện',
                              default=lambda s: s.env.uid,
                              readonly=True)

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        # print(defaults)
        # {}
        chk = self.env['lib.checkout.back.home'].sudo().search([('id', '=', self.env.context.get('active_id'))])
        if chk.book_id:
            defaults['book_id'] = chk.book_id.id
            defaults['meta_book_id'] = chk.meta_book_id.id
        elif chk.project_id:
            defaults['project_id'] = chk.project_id.id
            defaults['meta_project_id'] = chk.meta_project_id.id
        defaults['status_document'] = (chk.status_document if chk.status_document else '') + '. ' + (str(chk.note) if chk.note else '')
        return defaults

    @api.multi
    def button_update_description(self):
        if self.book_id:
            self.meta_book_id.write({'description': self.status_document})
            self.book_id.message_post(_('%s đã được cập nhật bởi %s' % (str(self.meta_book_id.name_seq), str(self.user_id.name))))
        elif self.project_id:
            self.meta_project_id.write({'description': self.status_document})
            self.project_id.message_post(_('%s đã được cập nhật bởi %s' % (str(self.meta_project_id.name_seq), str(self.user_id.name))))


