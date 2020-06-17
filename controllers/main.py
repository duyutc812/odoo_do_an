from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class CheckoutMagazineNewspaperController(http.Controller):

    @http.route('/do_an_tn/checkout_mg_new', auth='user', type='json')
    def checkout_mg_new_banner(self):
        return {
            'html': """
                
                        <center>
                        <h1 style="color:red">
                            Notice: Magazine and newspaper only borrowed at the library.
                        </h1>
        
                        </center>"""
        }