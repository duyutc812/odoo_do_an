from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CreateMetaProject(models.TransientModel):
    _name = 'create.meta.project'
    _description = 'Create Meta Project'

    project_id = fields.Many2one('document.project', string='Project')
    name_seq = fields.Char(string="Meta Project ID", default=lambda self: _('New'), readonly=True)
    description = fields.Text('Description', default='Tài liệu mới')
    state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', default='available')
    quantity = fields.Integer('Quantity')

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        pro = self.env['document.project'].search([('id', '=', self.env.context.get('active_id'))])
        defaults['project_id'] = pro.id
        return defaults

    @api.multi
    def button_create(self):
        meta_project = self.env['meta.projects']
        if not self.quantity:
            raise ValidationError(_('The Quantity must be greater than 0!'))
        for k in range(1, self.quantity+1):
            project_fields = list(meta_project._fields)
            project_vals = meta_project.default_get(project_fields)
            project_vals.update({'project_id': self.project_id.id,
                                 'description': self.description,
                                 'state': 'available'})
            meta_project.create(project_vals)
        self.project_id.message_post(_('%s updated quantity of %s is %s' % (str(self.create_uid.name), str(self.project_id.name), str(self.quantity))))
        return True


