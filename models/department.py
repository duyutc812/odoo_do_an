from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Department(models.Model):
    _name = 'lib.department'
    _description = 'Phòng ban'

    name = fields.Char('Phòng ban', related='group_id.name', store=True)
    category_id = fields.Many2one('ir.module.category', string='Ứng dụng', readonly=True,
                                  default=lambda s: s.env.ref('do_an_tn.module_library_category').id)
    group_id = fields.Many2one('res.groups', string="Nhóm")
    count_employee = fields.Integer(compute='_compute_count_employee')

    _sql_constraints = [
        ('group_id_uniq',
         'unique(group_id)',
         'Nhóm đã tồn tại!'),
    ]

    @api.constrains('category_id', 'group_id')
    def _constrains_cate_id_group_id(self):
        if self.category_id != self.group_id.category_id:
            raise ValidationError(_('Hãy chọn lại nhóm!'))

    @api.onchange('group_id')
    def _onchange_group_id(self):
        return {'domain': {'group_id': [('category_id', '=', self.category_id.id)]}}

    @api.multi
    def open_employee(self):
        librarian_id = self.env.ref('do_an_tn.library_group_librarian').id
        manager_id = self.env.ref('do_an_tn.library_group_manager').id
        if self.group_id.id in [librarian_id, manager_id]:
            domain = [('groups_id', '=', self.group_id.id)]
        else:
            domain = [('groups_id', 'not in', [librarian_id, manager_id])]

        return {
            'name': _('Nhân viên : %s' % (self.name)),
            'domain': domain,
            'view_type': 'form',
            'res_model': 'res.users',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'type': 'ir.actions.act_window',
        }

    # @api.multi
    # def _compute_count_employee(self):
    #     for dep in self:
    #         dep.count_employee = self.env['res.users'].search_count([('groups_id', '=', self.group_id.id)])
