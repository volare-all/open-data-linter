import pandas as pd
from jeraconv import jeraconv
from typing import Pattern

from .regex import (
    EMPTY_REGEX_LIST,
    VALID_PREFECTURE_NAME,
    INVALID_PREFECTURE_NAME,
)
from .vo import LintResult


def is_number(elem):
    """
    数値に変換可能か判定
    """
    if pd.isnull(elem):
        return False
    try:
        float(elem)
    except ValueError:
        return False
    return True


def is_string(elem):
    """
    数値を含まない文字列であるか判定
    """
    if is_empty(elem):
        return False

    if is_include_number(elem):
        return False

    return True


def is_integer(elem):
    """
    整数に変換可能(小数点を含まない)であるか判定
    """
    if not is_number(elem):
        return False

    return float(elem).is_integer()


def is_prefecture_code(elem):
    """
    都道府県コードに含まれるか判定
    """
    if not is_integer(elem):
        return False

    return 0 < int(float(elem)) and int(float(elem)) <= 47


def is_prefecture_name(elem):
    """
    都道府県名であるか判定
    """
    return elem in (VALID_PREFECTURE_NAME + INVALID_PREFECTURE_NAME)


def is_empty(elem):
    """
    sが空のセル相当であるか
    TODO: str型以外の場合を検討していない(nullなど)
    """
    if pd.isnull(elem):
        return True
    if type(elem) is str and any(
            [r.match(str(elem)) is not None for r in EMPTY_REGEX_LIST]):
        return True


def is_include_number(elem):
    """
    文字列sに数字が含まれているか
    """
    if pd.isnull(elem):
        return False

    return any(map(str.isdigit, str(elem)))


def is_jp_calendar_year(j2w: jeraconv.J2W, year_str: str) -> bool:
    try:
        j2w.convert(year_str)
        return True
    except ValueError:
        return False


def is_valid_date(cell: str, regex: Pattern, year: int) -> bool:
    result = regex.match(cell)
    if result is None:
        return False
    return int(result.groups()[0]) == year


def before_check_1_1(func):
    def wrapper(self, *args, **kwargs):
        if not self.check_1_1().is_valid:
            return LintResult.gen_simple_error_result(
                "ファイルが読み込めなかったため、チェックできませんでした。", is_valid=None)
        return func(self, *args, **kwargs)

    return wrapper
