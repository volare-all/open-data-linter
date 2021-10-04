from enum import Enum
from typing import Dict, Tuple

from jeraconv import jeraconv

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

    def perform(self):
        return [
            self.__get_column_type(ci) for ci in range(len(self.df.columns))
        ]

    def __get_column_type(self, column_index: int) -> ColumnType:
        counts, empty_count = self.__count_elements_and_empty(column_index)
        return self.__get_plausible_column_type(counts, empty_count)

    def __count_elements_and_empty(
            self, column_index: int) -> Tuple[Dict[ColumnType, int], int]:
        empty_count = 0
        counts = {
            ColumnType.PREFECTURE_CODE: 0,
            ColumnType.CHRISTIAN_ERA: 0,
            ColumnType.DATETIME_CODE: 0,
            ColumnType.OTHER_NUMBER: 0,
            ColumnType.PREFECTURE_NAME: 0,
            ColumnType.OTHER_STRING: 0,
            ColumnType.JP_CALENDAR_YEAR: 0,
            ColumnType.NONE_CATEGORY: 0
        }
        column = self.df.iloc[:, column_index]

        j2w = jeraconv.J2W()
        for elem in column:
            if is_empty(elem):
                empty_count += 1
            elif is_prefecture_code(elem):
                counts[ColumnType.PREFECTURE_CODE] += 1
                counts[ColumnType.CHRISTIAN_ERA] += 1
                counts[ColumnType.OTHER_NUMBER] += 1
            elif is_match_regex(CHRISTIAN_ERA_REGEX, elem):
                counts[ColumnType.CHRISTIAN_ERA] += 1
                counts[ColumnType.OTHER_NUMBER] += 1
            elif is_match_regex(DATETIME_CODE_REGEX, elem):
                counts[ColumnType.DATETIME_CODE] += 1
                counts[ColumnType.OTHER_NUMBER] += 1
            elif is_number(elem):
                counts[ColumnType.OTHER_NUMBER] += 1
            elif is_prefecture_name(elem):
                counts[ColumnType.PREFECTURE_NAME] += 1
                counts[ColumnType.OTHER_STRING] += 1
            elif is_string(elem):
                counts[ColumnType.OTHER_STRING] += 1
            elif is_jp_calendar_year(j2w, elem):
                counts[ColumnType.JP_CALENDAR_YEAR] += 1
            else:
                counts[ColumnType.NONE_CATEGORY] += 1

        return counts, empty_count

    def __get_plausible_column_type(self, counts: Dict[ColumnType, int],
                                    empty_count: int) -> ColumnType:
        if len(self.df) == empty_count:
            return ColumnType.NONE_CATEGORY

        priority = [
            ColumnType.PREFECTURE_CODE, ColumnType.CHRISTIAN_ERA,
            ColumnType.DATETIME_CODE, ColumnType.OTHER_NUMBER,
            ColumnType.PREFECTURE_NAME, ColumnType.OTHER_STRING,
            ColumnType.JP_CALENDAR_YEAR, ColumnType.NONE_CATEGORY
        ]

        plausible_type = None
        max_count = 0
        for t in priority:
            if counts[t] > max_count:
                plausible_type = t
                max_count = counts[t]

        if max_count / (len(self.df) - empty_count) > self.classify_rate:
            return plausible_type
        else:
            return ColumnType.NONE_CATEGORY
