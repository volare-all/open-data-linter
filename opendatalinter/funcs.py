import pandas as pd

from .vo import LintResult


def is_num(s):
    """
    数値に変換可能か判定
    """
    if pd.isnull(s):
        return False
    try:
        float(s)
    except ValueError:
        return False
    return True


def before_check_1_1(func):
    def wrapper(self, *args, **kwargs):
        if not self.check_1_1().is_valid:
            return LintResult.gen_simple_error_result(
                "ファイルが読み込めなかったため、チェックできませんでした。", is_valid=None)
        return func(self, *args, **kwargs)

    return wrapper
