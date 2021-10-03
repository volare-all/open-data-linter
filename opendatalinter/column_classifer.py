import re
import pandas as pd
from jeraconv import jeraconv
from enum import Enum

from .funcs import (is_number,
                    is_string,
                    is_prefecture_code,
                    is_prefecture_name,
                    is_match_regex,
                    is_empty,
                    is_jp_calendar_year
                    )
from .regex import (CHRISTIAN_ERA_REGEX,
                    DATETIME_CODE_REGEX,
                    VALID_PREFECTURE_NAME,
                    INVALID_PREFECTURE_NAME
                    )


class ColumnType(Enum):
    PREFECTURE_CODE = 'prefecture_code'
    PREFECTURE_NAME = 'prefecture_name'
    CHRISTIAN_ERA = 'christian_era'
    DATETIME_CODE = 'datetime_code'
    JP_CALENDAR_YEAR = 'jp_calendar_year'
    NUMBER = 'number'
    STRING = 'string'
    OTHER = 'other'


class ColumnClassifer:
    CLASSIFY_RATE = 0.8  # 列の分類の判定基準(値が含まれているセル数 / (列の長さ - 空のセル))

    def __init__(self, df):
        self.df = df

    def perform(self):
        result = []

        for i in range(len(self.df.columns)):
            column = self.df.iloc[:, i]

            classes = {
                ColumnType.PREFECTURE_CODE: False,
                ColumnType.PREFECTURE_NAME: False,
                ColumnType.CHRISTIAN_ERA: False,
                ColumnType.DATETIME_CODE: False,
                ColumnType.JP_CALENDAR_YEAR: False,
                ColumnType.NUMBER: False,
                ColumnType.STRING: False,
                ColumnType.OTHER: False
            }

            empty_counter = 0  # 空データに該当するもの
            items_counter = {
                ColumnType.PREFECTURE_CODE: 0,
                ColumnType.PREFECTURE_NAME: 0,
                ColumnType.CHRISTIAN_ERA: 0,
                ColumnType.DATETIME_CODE: 0,
                ColumnType.JP_CALENDAR_YEAR: 0,
                ColumnType.NUMBER: 0,
                ColumnType.STRING: 0,
                ColumnType.OTHER: 0
            }

            for elem in column:
                if is_empty(elem):
                    empty_counter += 1

                elif is_number(elem):
                    items_counter[ColumnType.NUMBER] += 1

                    if is_prefecture_code(elem):
                        items_counter[ColumnType.PREFECTURE_CODE] += 1

                    if is_match_regex(CHRISTIAN_ERA_REGEX, elem):
                        items_counter[ColumnType.CHRISTIAN_ERA] += 1

                    if is_match_regex(DATETIME_CODE_REGEX, elem):
                        items_counter[ColumnType.DATETIME_CODE] += 1
                elif is_string(elem):
                    items_counter[ColumnType.STRING] += 1

                    if is_prefecture_name(elem):
                        items_counter[ColumnType.PREFECTURE_NAME] += 1
                else:
                    if is_jp_calendar_year(jeraconv.J2W(), elem):
                        items_counter[ColumnType.JP_CALENDAR_YEAR] += 1
                        continue

                    items_counter[ColumnType.OTHER] += 1

            # print(f"items_counter: {items_counter}")

            for key, value in items_counter.items():
                try:
                    if value / (len(self.df) - empty_counter) > self.CLASSIFY_RATE:
                        classes[key] = True
                except ZeroDivisionError:
                    pass

            result.append(classes)

        return result
