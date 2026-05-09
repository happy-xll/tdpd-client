"""
Example program to demonstrate Gooey's presentation of subparsers
"""

import argparse

from gooey import Gooey, GooeyParser
from message import display_message
from chn_trans_data import trans_data_to_tdpd
from pdf2excel import pdfdf2excel
from tdpd2excel import paramgroup2excel
running = True

@Gooey(optional_cols=2, program_name="TDPD client", encoding='cp936')
def main():
    settings_msg = 'A GUI client for the TDPD params ' \
                   'for export import'
    parser = GooeyParser(description=settings_msg)
    parser.add_argument('--verbose', help='be verbose', dest='verbose',
                        action='store_true', default=False)
    subs = parser.add_subparsers(help='commands', dest='command')

    pdf2excel_parser = subs.add_parser(
        'pdf2excel', help='The any country pdf to excel')
    pdf2excel_parser.add_argument('--year',
                              help='Give The pdf year',
                              default= 2022,
                              type=int)
    pdf2excel_parser.add_argument('--month',
                              help='give the pdf month',
                              default = 12,
                              type=int)
    pdf2excel_parser.add_argument('--excel',
                              help='select the save excel path and file',
                              widget='FileSaver',
                              type=str)
    # ########################################################

    trans_parser = subs.add_parser(
        'upload_chn_trans_data', help='Upload chn trans param to the TDPD')
    trans_parser.add_argument('excel',
                             help='The excel file need to upload',
                             type=str, widget='FileChooser')
    # ########################################################

    tdpd2excel_parser = subs.add_parser(
        'tdpd2excel', help='Export TDPD param value to excel')

    tdpd2excel_parser.add_argument('--group',
                             default=1,
                             help='The Param Group')
    tdpd2excel_parser.add_argument('--year',
                              help='Give The pdf year',
                              default= 2022,
                              type=int)
    tdpd2excel_parser.add_argument('--excel',
                              help='select the output file location',
                              widget='FileSaver',
                              type=str)

    args = parser.parse_args()
    print(args)
    if args.command == 'pdf2excel':
        pdfdf2excel(args.year, args.month, args.excel)
    elif args.command == 'upload_chn_trans_data':
        trans_data_to_tdpd(args.excel)
    elif args.command == 'tdpd2excel':
        paramgroup2excel(args.excel, args.group, args.year)
    display_message()

if __name__ == '__main__':
    main()
