import csv
from io import StringIO

from .vo import LintResult


def to_csv_format(txt):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(txt)
    return output.getvalue()


def before_check_1_1(func):
    def wrapper(self, *args, **kwargs):
        if not self.check_1_1().is_valid:
            return LintResult.gen_simple_error_result(
                "ファイルが読み込めなかったため、チェックできませんでした。", is_valid=None)
        return func(self, *args, **kwargs)

    return wrapper
