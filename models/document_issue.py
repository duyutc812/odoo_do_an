from odoo import api, fields, models, _


class DocumentIssue(models.Model):
    _name = 'document.issue'
    _description = 'Document Issue'

    name_seq = fields.Char(string="Doc Issue ID", default=lambda self: _('New'), readonly=True)
    document_name = fields.Char('Document Name')
    meta_doc = fields.Char('Meta Doc')
    borrow_date = fields.Datetime('Borrow date')
    return_date = fields.Datetime('Return date')
    description_bor = fields.Char('Description Borrow')
    description_ret = fields.Char('Description Return')
    checkout_id = fields.Char('Checkout ID')
