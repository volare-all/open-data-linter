from enum import Enum

from .funcs import (is_number, is_string, is_prefecture_code,
                    is_prefecture_name, is_match_regex, is_empty,
                    is_jp_calendar_year)
from .regex import (
    CHRISTIAN_ERA_REGEX,
    DATETIME_CODE_REGEX,
)


class ColumnType(Enum):
    PREFECTURE_CODE = 'prefecture_code'
    PREFECTURE_NAME = 'prefecture_name'
    CHRISTIAN_ERA = 'christian_era'
    DATETIME_CODE = 'datetime_code'
    JP_CALENDAR_YEAR = 'jp_calendar_year'
    OTHER_NUMBER = 'other_number'
    OTHER_STRING = 'other_string'
    NONE_CATEGORY = 'none_category'

    @classmethod
    def is_number(cls, column_type):
        if column_type in [
                cls.PREFECTURE_CODE, cls.CHRISTIAN_ERA, cls.DATETIME_CODE,
                cls.OTHER_NUMBER
        ]:
            return True
        return False

    @classmethod
    def is_string(cls, column_type):
        if column_type in [cls.PREFECTURE_NAME, cls.OTHER_STRING]:
            return True
        return False


class ColumnClassifer:
    DEFAULT_CLASSIFY_RATE = 0.8  # 列の分類の判定基準(値が含まれているセル数 / (列の長さ - 空のセル))

    def __init__(self, df, classify_rate=None):
        self.df = df
        self.classify_rate = self.DEFAULT_CLASSIFY_RATE if classify_rate is None else classify_rate

    def perform(self, j2w):
        def is_match_category(category, items_counter, empty_counter):
            try:
                if items_counter[category] / (
                        len(self.df) - empty_counter) > self.classify_rate:
                    return True
            except:
                pass
            return False

        result = []

        for i in range(len(self.df.columns)):
            column = self.df.iloc[:, i]

            empty_counter = 0  # 空データに該当するもの
            items_counter = {
                ColumnType.PREFECTURE_CODE: 0,
                ColumnType.PREFECTURE_NAME: 0,
                ColumnType.CHRISTIAN_ERA: 0,
                ColumnType.DATETIME_CODE: 0,
                ColumnType.JP_CALENDAR_YEAR: 0,
                ColumnType.OTHER_NUMBER: 0,
                ColumnType.OTHER_STRING: 0,
                ColumnType.NONE_CATEGORY: 0
            }

            for elem in column:
                if is_empty(elem):
                    empty_counter += 1

                elif is_number(elem):
                    items_counter[ColumnType.OTHER_NUMBER] += 1

                    if is_prefecture_code(elem):
                        items_counter[ColumnType.PREFECTURE_CODE] += 1

                    if is_match_regex(CHRISTIAN_ERA_REGEX, elem):
                        items_counter[ColumnType.CHRISTIAN_ERA] += 1

                    if is_match_regex(DATETIME_CODE_REGEX, elem):
                        items_counter[ColumnType.DATETIME_CODE] += 1
                elif is_string(elem):
                    items_counter[ColumnType.OTHER_STRING] += 1

                    if is_prefecture_name(elem):
                        items_counter[ColumnType.PREFECTURE_NAME] += 1
                else:
                    if is_jp_calendar_year(j2w, elem):
                        items_counter[ColumnType.JP_CALENDAR_YEAR] += 1
                        continue

                    items_counter[ColumnType.NONE_CATEGORY] += 1

            if is_match_category(ColumnType.OTHER_NUMBER, items_counter, empty_counter):
                if is_match_category(ColumnType.DATETIME_CODE, items_counter, empty_counter):
                    result.append(ColumnType.DATETIME_CODE)
                    continue

                if is_match_category(ColumnType.CHRISTIAN_ERA, items_counter, empty_counter):
                    if is_match_category(ColumnType.PREFECTURE_CODE, items_counter, empty_counter):
                        result.append(ColumnType.PREFECTURE_CODE)
                        continue

                    result.append(ColumnType.CHRISTIAN_ERA)
                    continue

                result.append(ColumnType.OTHER_NUMBER)
                continue

            if is_match_category(ColumnType.OTHER_STRING, items_counter, empty_counter):
                if is_match_category(ColumnType.PREFECTURE_NAME, items_counter, empty_counter):
                    result.append(ColumnType.PREFECTURE_NAME)
                    continue

                result.append(ColumnType.OTHER_STRING)
                continue

            if is_match_category(ColumnType.JP_CALENDAR_YEAR, items_counter, empty_counter):
                result.append(ColumnType.JP_CALENDAR_YEAR)
                continue

            result.append(ColumnType.NONE_CATEGORY)

        return result
