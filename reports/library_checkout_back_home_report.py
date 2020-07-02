from odoo import api, models, _, fields
from odoo.exceptions import ValidationError
from datetime import datetime, date
import pytz


class LibraryCheckoutReport(models.AbstractModel):
    # _name :report.module_name.report_name
    _name = 'report.do_an_tn.report_library_checkout_template'
    _description = 'Library Checkout Back Home Report'

    # call a python function while printing report PDF
    # https://www.odoo.com/documentation/12.0/reference/reports.html#custom-reports
    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        print('docids', docids)
        # docs = self.env['hospital.patient'].browse(docids[0])
        checkouts = self.env['library.checkout.back.home'].sudo().search([('id', 'in', docids)])
        checkouts_list = []
        user_list = []
        doc = checkouts[0]
        current_date = datetime.now()
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_today = pytz.utc.localize(current_date).astimezone(user_tz)
        curr_date_lst = [{'curr_date': date_today}]
        chk_set = {x.card_id.id for x in checkouts}
        if len(chk_set) != 1:
            checkouts_list = []
            self.env.user.notify_danger(title='Error', message='Please select records with 1 card!')
        else:
            user_list = [{'user': self.env.user.name}]
            for chk in checkouts:
                if chk.state == 'draft':
                    self.env.user.notify_danger(title='Error', message='Chọn bản ghi khác draft !')
                    checkouts_list = []
                    break
                vals = {
                    'card_id': chk.card_id.code,
                    'gt_name': chk.gt_name,
                    'name_seq': chk.name_seq,
                    'title_doc': str(chk.book_id.name if chk.book_id else chk.project_id.name),
                    'doc_id': str(chk.meta_book_id.name_get()[0][1] if chk.meta_book_id else chk.meta_project_id.name_get()[0][1]),
                    'return_appointment_date': chk.return_date,
                    'category_doc': chk.category_doc,
                    'currency_id': chk.currency_id,
                    'price_doc': chk.price_doc,
                    'status_doc': chk.status_document,
                    'actual_return_date': chk.actual_return_date if chk.actual_return_date else '',
                }
                checkouts_list.append(vals)

            print('checkouts', checkouts)
            print('checkouts_list', checkouts_list)
        return {
            'doc_model': 'library.checkout.back.home',
            'data': data,
            'user_list': user_list,
            'doc': doc,
            'checkouts_list': checkouts_list,
            'curr_date_lst': curr_date_lst,
        }


class PenaltyCheckoutAtLib(models.AbstractModel):
    _name = 'report.do_an_tn.report_penalty_at_lib_xls'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Penalty Checkout At Lib Excel Report'

    def generate_xlsx_report(self, workbook, data, lines):
        format1 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
        format2 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        # One sheet by partner
        sheet = workbook.add_worksheet('Penalty Checkout At Lib')
        # print excel report in right to left format
        # sheet.right_to_left()
        if lines.state not in ['fined', 'lost']:
            sheet.write(2, 2, 'Invalid')
            return True
        else:
            sheet.write(2, 2, 'Card ID', format1)
            sheet.write(2, 3, lines.name_seq, format2)
            sheet.write(3, 2, 'Name', format1)
            sheet.write(3, 3, lines.gt_name, format2)
            sheet.write(4, 2, 'Type Doc', format1)
            sheet.write(4, 3, lines.type_document, format2)
            if lines.type_document == 'book':
                sheet.write(5, 2, 'Title Doc', format1)
                sheet.write(5, 3, lines.book_id.name, format2)
                sheet.write(6, 2, 'Doc ID', format1)
                sheet.write(6, 3, lines.meta_book_id.name_seq, format2)
            elif lines.project_id:
                sheet.write(5, 2, 'Title Doc', format1)
                sheet.write(5, 3, lines.project_id.name, format2)
                sheet.write(6, 2, 'Doc ID', format1)
                sheet.write(6, 3, lines.meta_project_id.name_seq, format2)
            elif lines.mgz_new_id:
                sheet.write(5, 2, 'Title Doc', format1)
                sheet.write(5, 3, lines.mgz_new_id.name_get()[0][1], format2)
                sheet.write(6, 2, 'Doc ID', format1)
                sheet.write(6, 3, lines.meta_mgz_new_id.name_seq, format2)
            sheet.write(7, 2, 'Description', format1)
            sheet.write(7, 3, lines.status_document, format2)
            sheet.write(8, 2, 'Price', format1)
            sheet.write(8, 3, lines.price_doc, format2)
            sheet.write(9, 2, 'Return Date', format1)
            sheet.write(9, 3, lines.return_date.strftime('%d-%m-%Y'), format2)
            sheet.write(10, 2, 'Penalty Price', format1)
            sheet.write(10, 3, lines.price_penalty, format2)
            sheet.write(11, 2, 'Note', format1)
            sheet.write(11, 3, lines.note, format2)
