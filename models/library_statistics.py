from odoo import api, fields, models, _


class LibraryStatistics(models.Model):
    _name = 'library.statistics'
    _description = 'Library Statistics'

    create_date = fields.Datetime(string="Create Date")
    num_book = fields.Integer()
