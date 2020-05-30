from odoo import api, models, _


class CheckoutReport(models.AbstractModel):
    _name = 'report.do_an_tn.report_library_checkout_template'
    _description = 'Checkout Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        print(model)
        print('docids', docids)
        docs = self.env['library.checkout'].browse(docids[0])
        print(docs)
        print(data)



