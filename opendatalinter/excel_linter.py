import csv
import io

import openpyxl
import pandas as pd

from .csv_linter import CSVLinter


def ws2csv(ws) -> str:
    with io.StringIO() as s:
        writer = csv.writer(s)
        for row in ws.rows:
            writer.writerow([cell.value for cell in row])
        return s.getvalue()


class ExcelLinter:
    def __getattr__(self, name):
        return getattr(self.csv_linter, name)

    def __init__(self,
                 data: bytes,
                 filename: str,
                 title_line_num=None,
                 header_line_num=None):
        with io.BytesIO(data) as f:
            wb = openpyxl.load_workbook(f)
            # df = pd.read_excel(f, header=None)

        # ToDo: どのシートを見る?
        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            text = ws2csv(ws)
            break

        self.wb = wb
        self.csv_linter = CSVLinter(text.encode(),
                                    "from_excel.csv",
                                    title_line_num=title_line_num,
                                    header_line_num=header_line_num)

    def check_1_4(self):
        # ToDo: impl
        for sheetname in self.wb.sheetnames:
            ws = self.wb[sheetname]
            print(dir(ws))
            print(ws)
            print(ws.cell(5, 1).value)
            print(ws.cell(5, 2).value)
            print(ws.cell(19, 1).value)
            text = ws2csv(ws)
            linter = CSVLinter(text.encode(), "test.csv")
            print(linter.check_1_3())
            for merged_cell in ws.merged_cells:
                print(merged_cell.bounds)
                print(merged_cell.size)
            break
