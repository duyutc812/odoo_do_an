from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CreateMetaProject(models.TransientModel):
    _name = 'create.meta.project'
    _description = 'Create Meta Project'

    project_id = fields.Many2one('lib.document.project', string='Đồ án/luận văn')
    name_seq = fields.Char(string="Mã meta Đồ án/Luận văn", default=lambda self: _('New'), readonly=True)
    description = fields.Text('Tình trạng', default='Tài liệu mới')
    state = fields.Selection([
        ('available', 'Có sẵn'),
        ('not_available', 'Không có sẵn')
    ], string='Trạng thái', default='available')
    quantity = fields.Integer('Số lượng')

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        pro = self.env['lib.document.project'].sudo().search([('id', '=', self.env.context.get('active_id'))])
        defaults['project_id'] = pro.id
        return defaults

    @api.multi
    def button_create(self):
        meta_project = self.env['lib.meta.projects']
        if not self.quantity:
            raise ValidationError(_('Số lượng phải lớn hơn 0!'))
        for k in range(1, self.quantity+1):
            project_fields = list(meta_project._fields)
            project_vals = meta_project.default_get(project_fields)
            project_vals.update({'project_id': self.project_id.id,
                                 'description': self.description,
                                 'state': 'available'})
            meta_project.create(project_vals)
        self.project_id.message_post(_('%s đã cập nhật số lượng của \'%s\' là %s' % (str(self.create_uid.name), str(self.project_id.name), str(self.quantity))))
        return True


