from odoo import api, models, _, fields
from odoo.exceptions import ValidationError
from datetime import datetime, date
import pytz


class LibraryCheckoutReport(models.AbstractModel):
    _name = 'report.do_an_tn.report_library_checkout_template'
    _description = 'In phiếu mượn về'

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        print('docids', docids)
        checkouts = self.env['lib.checkout.back.home'].sudo().search([('id', 'in', docids)])
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
            self.env.user.notify_danger(_(title='Lỗi', message='Chỉ được chọn phiếu mượn của 1 thẻ mượn!'))
        else:
            user_list = [{'user': self.env.user.name}]
            for chk in checkouts:
                if chk.state != 'running':
                    self.env.user.notify_danger(title=_('Lỗi'), message=_('Không thể chọn bản ghi khác \'Đã mượn\'!'))
                    checkouts_list = []
                    break
                vals = {
                    'card_id': chk.card_id.name_seq,
                    'gt_name': chk.gt_name,
                    'name_seq': chk.name_seq,
                    'title_doc': str(chk.book_id.name if chk.book_id else chk.project_id.name),
                    'doc_id': str(chk.meta_book_id.name_get()[0][1] if chk.meta_book_id else chk.meta_project_id.name_get()[0][1]),
                    'return_appointment_date': chk.return_date,
                    'category_doc': chk.category_doc,
                    'currency_id': chk.currency_id,
                    'doc_price': chk.doc_price,
                    'status_doc': chk.status_document,
                    'actual_return_date': chk.actual_return_date if chk.actual_return_date else '',
                }
                checkouts_list.append(vals)

            print('checkouts', checkouts)
            print('checkouts_list', checkouts_list)
        return {
            'doc_model': 'lib.checkout.back.home',
            'data': data,
            'user_list': user_list,
            'doc': doc,
            'checkouts_list': checkouts_list,
            'curr_date_lst': curr_date_lst,
        }


class PenaltyCheckoutAtLib(models.AbstractModel):
    _name = 'report.do_an_tn.report_penalty_at_lib_xls'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'In phiếu phạt: mượn tại thư viện : Excel'

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
            sheet.write(2, 2, 'Thẻ thư viện', format1)
            sheet.write(2, 3, lines.name_seq, format2)
            sheet.write(3, 2, 'Tên độc giả', format1)
            sheet.write(3, 3, lines.gt_name, format2)
            sheet.write(4, 2, 'Loại tài liệu', format1)
            sheet.write(4, 3, lines.type_document, format2)
            if lines.type_document == 'book':
                sheet.write(5, 2, 'Tiêu đề sách', format1)
                sheet.write(5, 3, lines.book_id.name, format2)
                sheet.write(6, 2, 'Meta sách', format1)
                sheet.write(6, 3, lines.meta_book_id.name_seq, format2)
            elif lines.project_id:
                sheet.write(5, 2, 'Đồ án - luận văn', format1)
                sheet.write(5, 3, lines.project_id.name, format2)
                sheet.write(6, 2, 'Meta đồ án - luận văn', format1)
                sheet.write(6, 3, lines.meta_project_id.name_seq, format2)
            elif lines.mgz_new_id:
                sheet.write(5, 2, 'Tạp chí - báo', format1)
                sheet.write(5, 3, lines.mgz_new_id.name_get()[0][1], format2)
                sheet.write(6, 2, 'Doc ID', format1)
                sheet.write(6, 3, lines.meta_mgz_new_id.name_seq, format2)
            sheet.write(7, 2, 'Tình trạng', format1)
            sheet.write(7, 3, lines.status_document, format2)
            sheet.write(8, 2, 'Giá tài liệu', format1)
            sheet.write(8, 3, lines.doc_price, format2)
            sheet.write(9, 2, 'Ngày trả', format1)
            sheet.write(9, 3, lines.return_date.strftime('%d-%m-%Y'), format2)
            sheet.write(10, 2, 'Tiền phạt', format1)
            sheet.write(10, 3, lines.penalty_price, format2)
            sheet.write(11, 2, 'Ghi chú', format1)
            sheet.write(11, 3, lines.note, format2)


class PenaltyCheckoutBHReport(models.AbstractModel):
    _name = 'report.do_an_tn.report_penalty_checkout_bh_template'
    _description = 'In phiếu phạt: mượn về nhà'

    @api.model
    def _get_report_values(self, docids, data=None):
        # docs = self.env['hospital.patient'].browse(docids[0])
        checkouts = self.env['lib.checkout.back.home'].sudo().search([('id', 'in', docids)])
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
            self.env.user.notify_danger(_(title='Lỗi', message='Chọn các bản ghi của cùng 1 thẻ thư viện'))
        else:
            user_list = [{'user': self.env.user.name}]
            for chk in checkouts:
                if chk.state not in ['fined', 'lost']:
                    self.env.user.notify_danger(title=_('Error'),
                                                message=_('Không thể chọn các bản ghi ở trạng thái khác '
                                                          '\'Bị phạt , Mất tài liệu\'!'))
                    checkouts_list = []
                    break
                vals = {
                    'card_id': chk.card_id.name_seq,
                    'gt_name': chk.gt_name,
                    'name_seq': chk.name_seq,
                    'title_doc': str(chk.book_id.name if chk.book_id else chk.project_id.name),
                    'doc_id': str(chk.meta_book_id.name_get()[0][1] if chk.meta_book_id else chk.meta_project_id.name_get()[0][1]),
                    'return_appointment_date': chk.return_date,
                    'category_doc': chk.category_doc,
                    'currency_id': chk.currency_id,
                    'doc_price': chk.doc_price,
                    'status_doc': chk.status_document,
                    'actual_return_date': chk.actual_return_date if chk.actual_return_date else '',
                    'overdue': chk.day_overdue,
                    'penalty_chk_price': chk.penalty_chk_price,
                    'penalty_doc_price': chk.penalty_doc_price,
                    'penalty_total': chk.penalty_total,
                    'note': chk.note,
                }
                checkouts_list.append(vals)
        return {
            'doc_model': 'lib.checkout.back.home',
            'data': data,
            'user_list': user_list,
            'doc': doc,
            'checkouts_list': checkouts_list,
            'curr_date_lst': curr_date_lst,
        }

