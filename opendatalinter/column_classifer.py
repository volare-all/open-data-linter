import re
import pandas as pd
from jeraconv import jeraconv
from enum import Enum


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
    EMPTY_REGEX_LIST = list(
        map(lambda s: re.compile(s), [r'^\s*$', '-', 'ー', 'なし']))
    DATETIME_CODE_REGEX = re.compile(r"^(\d{4})[01][012]\d{4}$")
    CHRISTIAN_ERA_REGEX = re.compile(r"^(\d{1,4})年?$")

    VALID_PREFECTURE_NAME = [
        '北海道', '青森県', '岩手県', '宮城県', '秋田県',
        '山形県', '福島県', '茨城県', '栃木県', '群馬県',
        '埼玉県', '千葉県', '東京都', '神奈川県', '新潟県',
        '富山県', '石川県', '福井県', '山梨県', '長野県',
        '岐阜県', '静岡県', '愛知県', '三重県', '滋賀県',
        '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県',
        '鳥取県', '島根県', '岡山県', '広島県', '山口県',
        '徳島県', '香川県', '愛媛県', '高知県', '福岡県',
        '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県',
        '鹿児島県', '沖縄県'
    ]

    INVALID_PREFECTURE_NAME = [
        '青森', '岩手', '宮城', '秋田',
        '山形', '福島', '茨城', '栃木', '群馬',
        '埼玉', '千葉', '東京', '神奈川', '新潟',
        '富山', '石川', '福井', '山梨', '長野',
        '岐阜', '静岡', '愛知', '三重', '滋賀',
        '京都', '大阪', '兵庫', '奈良', '和歌山',
        '鳥取', '島根', '岡山', '広島', '山口',
        '徳島', '香川', '愛媛', '高知', '福岡',
        '佐賀', '長崎', '熊本', '大分', '宮崎',
        '鹿児島', '沖縄'
    ]

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
                if self.__is_empty(elem):
                    empty_counter += 1

                elif self.__is_number(elem):
                    items_counter[ColumnType.NUMBER] += 1

                    if self.__is_prefecture_code(elem):
                        items_counter[ColumnType.PREFECTURE_CODE] += 1

                    if self.__is_match_regex(self.CHRISTIAN_ERA_REGEX, elem):
                        items_counter[ColumnType.CHRISTIAN_ERA] += 1

                    if self.__is_match_regex(self.DATETIME_CODE_REGEX, elem):
                        items_counter[ColumnType.DATETIME_CODE] += 1
                elif self.__is_string(elem):
                    items_counter[ColumnType.STRING] += 1

                    if self.__is_prefecture_name(elem):
                        items_counter[ColumnType.PREFECTURE_NAME] += 1
                else:
                    if self.__is_jp_calendar_year(jeraconv.J2W(), elem):
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

    def __is_number(self, elem):
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

    def __is_string(self, elem):
        """
        数値を含まない文字列であるか判定
        """
        if self.__is_empty(elem):
            return False

        if self.__is_include_number(elem):
            return False

        return True

    def __is_integer(self, elem):
        """
        整数に変換可能(小数点を含まない)であるか判定
        """
        if not self.__is_number(elem):
            return False

        return float(elem).is_integer()

    def __is_prefecture_code(self, elem):
        """
        都道府県コードに含まれるか判定
        """
        if not self.__is_integer(elem):
            return False

        return 0 < int(float(elem)) and int(float(elem)) <= 47

    def __is_prefecture_name(self, elem):
        """
        都道府県名であるか判定
        """
        return elem in (self.VALID_PREFECTURE_NAME + self.INVALID_PREFECTURE_NAME)

    def __is_match_regex(self, regex, elem):
        result = regex.match(str(elem))
        if result is None:
            return False

        return True

    def __is_empty(self, s):
        """
        sが空のセル相当であるか
        TODO: str型以外の場合を検討していない(nullなど)
        """
        if pd.isnull(s):
            return True
        if type(s) is str and any(
                [r.match(str(s)) is not None for r in self.EMPTY_REGEX_LIST]):
            return True

    def __is_include_number(self, s):
        """
        文字列sに数字が含まれているか
        """
        if pd.isnull(s):
            return False

        return any(map(str.isdigit, s))

    @staticmethod
    def __is_jp_calendar_year(j2w: jeraconv.J2W, year_str: str) -> bool:
        try:
            j2w.convert(year_str)
            return True
        except ValueError:
            return False
