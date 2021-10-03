import os

from .excel_linter import ExcelLinter
from .csv_linter import CSVLinter


class OpenDataLinter:
    def __getattr__(self, name):
        return getattr(self.linter, name)

    def __init__(self,
                 data: bytes,
                 filename: str,
                 title_line_num=None,
                 header_line_num=None):

        exp = os.path.splitext(filename)[1]
        if exp in [".xls", ".xlsx", ".xlsm", ".xlsb", ".xlsxm"]:
            self.linter = ExcelLinter(data, filename)
        else:
            self.linter = CSVLinter(data, filename)
