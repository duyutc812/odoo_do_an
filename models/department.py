from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Project(models.Model):
    _name = 'lib.department'
    _description = 'Library Department'

    name = fields.Char('Department', related='group_id.name', store=True)
    category_id = fields.Many2one('ir.module.category', string='Category', readonly=True,
                                  default=lambda s: s.env.ref('do_an_tn.module_lib_category').id)
    group_id = fields.Many2one('res.groups', string="Group")
    count_employee = fields.Integer(compute='_compute_count_employee')

    _sql_constraints = [
        ('group_id_uniq',
         'unique(group_id)',
         'Group ID must be unique!'),
    ]

    @api.constrains('category_id', 'group_id')
    def _constrains_cate_id_group_id(self):
        if self.category_id != self.group_id.category_id:
            raise ValidationError(_('Let \'s select Group ID again!'))

    @api.onchange('group_id')
    def _onchange_group_id(self):
        return {'domain': {'group_id': [('category_id', '=', self.category_id.id)]}}

    @api.multi
    def open_employee(self):
        return {
            'name': _('Employees : %s' % (self.name)),
            'domain': [('groups_id', '=', self.group_id.id)],
            'view_type': 'form',
            'res_model': 'res.users',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def _compute_count_employee(self):
        for dep in self:
            dep.count_employee = self.env['res.users'].search_count([('groups_id', '=', self.group_id.id)])
