import csv
import io

import openpyxl

from .csv_linter import CSVLinter
from .vo import LintResult


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
            self.ws = wb[sheetname]
            self.text = ws2csv(self.ws)
            break

        self.wb = wb
        self.csv_linter = CSVLinter(self.text.encode(),
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

    def check_1_7(self):
        """
        数式を使⽤している場合は、数値データに修正しているか。
        '='から始まるセルをinvalidとみなす。
        """
        invalid_cells = []
        for r in range(0, self.ws.max_row):
            for c in range(0, self.ws.max_column):
                if str(self.ws.cell(r + 1, c + 1).value).startswith("="):
                    invalid_cells.append((r, c))
        return LintResult.gen_single_error_message_result(
            "数式が含まれています", invalid_cells)
