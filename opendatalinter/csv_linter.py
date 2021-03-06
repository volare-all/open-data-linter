import os
import re
import traceback
from dataclasses import dataclass
from functools import partial
from typing import List, Callable, Any, Pattern

import chardet
import numpy as np
from jeraconv import jeraconv

from .column_classifier import ColumnClassifier, ColumnType
from .csv_structure_analyzer import CSVStructureAnalyzer
from .errors import HeaderEstimateError
from .funcs import (
    before_check_1_1,
    is_number,
    is_empty,
    is_include_number,
)
from .regex import (
    SPACES_AND_LINE_BREAK_REGEX,
    DATETIME_CODE_REGEX,
    CHRISTIAN_ERA_REGEX,
    NUM_WITH_BRACKETS_REGEX,
    NUM_WITH_NUM_REGEX,
    VALID_PREFECTURE_NAME,
    INVALID_PREFECTURE_NAME,
    NUMBER_STRING_REGEX,
)
from .vo import LintResult, InvalidContent, InvalidCellFactory


@dataclass
class AdjacentColumnCondition:
    type: ColumnType
    predicate: Callable[[Any, Any], bool]


class CSVLinter:
    CLASSIFY_RATE = 0.8  # 列の分類の判定基準(値が含まれているセル数 / (列の長さ - 空のセル))

    def __init__(self,
                 data: bytes,
                 filename: str,
                 title_line_num=None,
                 header_line_num=None):
        self.cache = {}

        exp = os.path.splitext(filename)[1]
        if exp not in [".csv", ".CSV"]:
            self.cache["1-1"] = LintResult.gen_simple_error_result(
                "ファイルが読み込めませんでした。ファイル形式が Excel か CSV となっているか確認してください。")
            return

        try:
            self.data = data
            self.filename = filename
            self.text = self.__decode(data)

            csv_structure_analyzer = CSVStructureAnalyzer(self.text)
            self.title_line_num = csv_structure_analyzer.title_line_num if title_line_num is None else title_line_num
            self.header_line_num = csv_structure_analyzer.header_line_num if header_line_num is None else header_line_num
            self.header_invalid_cell_factory = InvalidCellFactory(
                self.title_line_num)
            self.content_invalid_cell_factory = InvalidCellFactory(
                self.title_line_num + self.header_line_num)

            self.header_df = csv_structure_analyzer.gen_header_df()
            self.df = csv_structure_analyzer.gen_rows_df()
            self.column_classify = ColumnClassifier(
                self.df, self.CLASSIFY_RATE).perform()
        except UnicodeDecodeError:
            if self.encoding == "utf-8":
                self.cache["1-1"] = LintResult.gen_simple_error_result(
                    "ファイルが読み込めませんでした。正しいファイルかどうか確認してください。")
            else:
                self.cache["1-1"] = LintResult.gen_simple_error_result(
                    "文字コードが読み取れませんでした。文字コードがutf-8になっているか確認してください。")
        except HeaderEstimateError:
            self.cache["1-1"] = LintResult.gen_simple_error_result(
                "ヘッダー部分の推定に失敗しました。")
        except Exception:
            traceback.print_exc()
            self.cache["1-1"] = LintResult.gen_simple_error_result(
                "未知のエラーが発生しました。お手数ですがサーバー運営者にお問い合わせください。")

    def check_1_1(self):
        """チェック項目1-1に沿って、ファイル形式が Excel か CSV となっているか確認する。
        """
        if "1-1" not in self.cache:
            self.cache["1-1"] = LintResult(True, [])
        return self.cache["1-1"]

    @before_check_1_1
    def check_1_2(self):
        """チェック項目2-2に沿って、1セル1データとなっているか確認する。
        """
        comma_separated_invalid_cells = []
        num_with_brackets_invalid_cells = []
        for i in range(len(self.df)):
            for j in range(len(self.df.columns)):
                v = self.df.iat[i, j]
                if not isinstance(v, str):
                    continue
                elms = re.split("[、,]", v)
                if len(elms) > 1:
                    for elm in elms:
                        m = NUM_WITH_BRACKETS_REGEX.match(
                            elm.strip())  # todo: もっと広いケースで通るように
                        if m is not None:
                            comma_separated_invalid_cells.append(
                                self.content_invalid_cell_factory.create(i, j))
                            break
                else:
                    for r in [NUM_WITH_BRACKETS_REGEX, NUM_WITH_NUM_REGEX]:
                        m = r.match(v.strip())
                        if m is not None:
                            num_with_brackets_invalid_cells.append(
                                self.content_invalid_cell_factory.create(i, j))
        invalid_contents = []
        if len(comma_separated_invalid_cells):
            invalid_contents.append(
                InvalidContent("句点によりデータが分割されています。",
                               comma_separated_invalid_cells))
        if len(num_with_brackets_invalid_cells):
            invalid_contents.append(
                InvalidContent("括弧によりデータが分割されています。",
                               num_with_brackets_invalid_cells))

        return LintResult(not (bool(len(invalid_contents))), invalid_contents)

    @before_check_1_1
    def check_1_3(self):
        """チェック項目1-3に沿って、数値データは数値属性とし、⽂字列を含まないことを確認する。

        Note:
            単位が列全てに含まれている場合、列ごとに警告する。
        """

        invalid_cells = []
        invalid_columns = []

        for j in range(len(self.df.columns)):
            column = self.df.iloc[:, j]

            # セルごとのチェック
            if self.column_classify[j].is_number():
                for i, elem in enumerate(column):
                    # TODO: 問題のあるセルの定義が以下の分岐で拾えているか要確認
                    if is_number(elem):
                        continue
                    if is_include_number(elem):
                        invalid_cells.append(
                            self.content_invalid_cell_factory.create(i, j))

            # 統一された列の単位チェック
            # TODO: sample/check_1_3の4列目のような列の判定を要確認
            if self.column_classify[j] == ColumnType.NONE_CATEGORY:
                empty_count = 0
                number_string_pattern_cell_count = 0  # ex.1000円

                for elem in column:
                    if is_empty(elem):
                        empty_count += 1
                        continue

                    if NUMBER_STRING_REGEX.match(str(elem)):
                        number_string_pattern_cell_count += 1

                if number_string_pattern_cell_count + empty_count == len(
                        self.df):
                    invalid_columns.append(
                        self.content_invalid_cell_factory.create(None, j))

        invalid_contents = []
        if len(invalid_cells):
            invalid_contents.append(
                InvalidContent("数値データに文字や空欄が含まれています。", invalid_cells))
        if len(invalid_columns):
            invalid_contents.append(
                InvalidContent("数値データの列に単位などの文字が含まれている可能性があります。",
                               invalid_columns))

        return LintResult(len(invalid_contents) == 0, invalid_contents)

    @before_check_1_1
    def check_1_4(self):
        """チェック項目1-4に沿って、セルの結合をしていないか確認する。（Excelのみ適用する）
        """
        return LintResult(True, [])

    @before_check_1_1
    def check_1_5(self):
        """チェック項目1-5に沿って、スペースや改⾏等で体裁を整えていないか確認する。

        Note:
            スペースと改行を1つ以上含む要素を invalid とみなす。
        """
        invalid_cells = []
        for df, invalid_cell_factory in [
            (self.header_df, self.header_invalid_cell_factory),
            (self.df, self.content_invalid_cell_factory)
        ]:
            is_formatted = df.applymap(lambda cell: SPACES_AND_LINE_BREAK_REGEX
                                       .match(str(cell)) is not None)
            indices = list(np.argwhere(is_formatted.values))
            invalid_cells.extend(
                map(lambda i: invalid_cell_factory.create(i[0], i[1]),
                    indices))

        return LintResult.gen_single_error_message_result(
            "スペースや改⾏が含まれています。", invalid_cells)

    @before_check_1_1
    def check_1_6(self):
        """チェック項目1-6に沿って、項⽬名等を省略していないか確認する。

        Note:
            ヘッダの欠損データを invalid とみなす。
        """
        invalid_cells = list(
            map(lambda t: self.header_invalid_cell_factory.create(t[0], t[1]),
                np.argwhere(self.header_df.isnull().values)))
        return LintResult.gen_single_error_message_result(
            "ヘッダーに空欄があります。", invalid_cells)

    @before_check_1_1
    def check_1_7(self):
        """チェック項目1-7に沿って、数式が使用されていないかを確認する。（Excelのみ適用する）
        """
        return LintResult(True, [])

    @before_check_1_1
    def check_1_10(self):
        """チェック項目1-10に沿って，機種依存⽂字を使⽤していないか確認する。

        Note:
            入力ファイルのエンコードが CP932 かつ shift_jis にデコードできない要素を invalid とみなす。
        """
        if self.encoding == "CP932":
            dfs = [self.header_df, self.df]
            start_row = self.title_line_num
            invalid_cells = []

            for df in dfs:
                is_formatted = df.applymap(
                    lambda cell: not self.__can_encode_from_cp932_to_sjis(
                        str(cell)))
                indices = list(np.argwhere(is_formatted.values))
                invalid_cells.extend(
                    map(lambda i: (i[0] + start_row, i[1]), indices))
                start_row += self.header_line_num

            return LintResult.gen_single_error_message_result(
                "機種依存⽂字が含まれています。", invalid_cells)

        return LintResult(True, [])

    def __can_encode_from_cp932_to_sjis(self, text: str) -> bool:
        try:
            text.encode(encoding="CP932").decode("shift_jis")
            return True
        except UnicodeDecodeError:
            return False

    @before_check_1_1
    def check_1_11(self):
        """チェック項目1-11に沿って、e-Stat の時間軸コードの表記、⻄暦表記⼜は和暦に⻄暦の併記がされているか確認する。

        Note:
            時刻コードもしくは西暦が隣接する列に併記されていない和暦の列を invalid とみなす。
        """
        j2w = jeraconv.J2W()

        def is_valid_element(jp_calendar: Any, adjacent: Any,
                             regex: Pattern) -> bool:
            try:
                target_year = j2w.convert(str(jp_calendar))
            except ValueError:
                return True

            if is_empty(jp_calendar):
                return True

            result = regex.match(str(adjacent))
            if result is None:
                return False
            return int(result.groups()[0]) == target_year

        invalid_columns = []
        conditions = [
            AdjacentColumnCondition(
                ColumnType.DATETIME_CODE,
                partial(is_valid_element, regex=DATETIME_CODE_REGEX)),
            AdjacentColumnCondition(
                ColumnType.CHRISTIAN_ERA,
                partial(is_valid_element, regex=CHRISTIAN_ERA_REGEX)),
        ]

        for column in range(len(self.df.columns)):
            if not self.column_classify[column] == ColumnType.JP_CALENDAR_YEAR:
                continue

            if not self.__check_adjacent_columns(column, conditions):
                invalid_columns.append(
                    self.content_invalid_cell_factory.create(None, column))

        return LintResult.gen_single_error_message_result(
            "和暦に適切な時間軸コードまたは⻄暦が併記されていません。", invalid_columns)

    @before_check_1_1
    def check_1_12(self):
        """チェック1-12に沿って、地域コードまたは地域名称が表記されているか確認する

        Note:
            都道府県のみチェックしている。表記揺れしている都道府県名もしくは，
            都道府県コードが隣接する列に併記されていない，都道府県名が省略された列を invalid とみなす
        """

        prefectures_numbers = {
            '北海道': 1,
            '青森': 2,
            '岩手': 3,
            '宮城': 4,
            '秋田': 5,
            '山形': 6,
            '福島': 7,
            '茨城': 8,
            '栃木': 9,
            '群馬': 10,
            '埼玉': 11,
            '千葉': 12,
            '東京': 13,
            '神奈川': 14,
            '新潟': 15,
            '富山': 16,
            '石川': 17,
            '福井': 18,
            '山梨': 19,
            '長野': 20,
            '岐阜': 21,
            '静岡': 22,
            '愛知': 23,
            '三重': 24,
            '滋賀': 25,
            '京都': 26,
            '大阪': 27,
            '兵庫': 28,
            '奈良': 29,
            '和歌山': 30,
            '鳥取': 31,
            '島根': 32,
            '岡山': 33,
            '広島': 34,
            '山口': 35,
            '徳島': 36,
            '香川': 37,
            '愛媛': 38,
            '高知': 39,
            '福岡': 40,
            '佐賀': 41,
            '長崎': 42,
            '熊本': 43,
            '大分': 44,
            '宮崎': 45,
            '鹿児島': 46,
            '沖縄': 47
        }

        # 都道府県名に該当するセルのうち，完全な都道府県名で列が構成されている場合True
        def is_valid_prefecture_name_column(c_index):
            for name in self.df.iloc[:, c_index]:
                if is_empty(name):
                    continue

                if name in INVALID_PREFECTURE_NAME:
                    return False
            return True

        # 都道府県を省略した記法で統一されている場合True
        def is_invalid_column(c_index):
            for name in self.df.iloc[:, c_index]:
                if name == '北海道':
                    continue

                if is_empty(name):
                    continue

                if name in VALID_PREFECTURE_NAME:
                    return False

            return True

        def is_invalid_cell(cell):
            if is_empty(name):
                return False

            if cell in INVALID_PREFECTURE_NAME:
                return True
            return False

        def is_valid_prefecture_with_prefecture_code(name: Any, number: Any):
            if not (isinstance(name, str) and isinstance(number, int)):
                return False

            return is_empty(name) or \
                   (name == '北海道' and str(number) == '1') or \
                   prefectures_numbers[name] == number

        invalid_cells = []
        invalid_columns = []
        conditions = [
            AdjacentColumnCondition(ColumnType.PREFECTURE_CODE,
                                    is_valid_prefecture_with_prefecture_code)
        ]

        # 都道府県名に分類される列ごとに判定
        for j in range(len(self.df.columns)):
            if not self.column_classify[j] == ColumnType.PREFECTURE_NAME:
                continue

            # 都道府県名に該当するセルのうち，完全な都道府県名で列が構成されている場合valid
            if is_valid_prefecture_name_column(j):
                continue

            # 列の中で一部が省略されている場合
            if not is_invalid_column(j):
                for i, name in enumerate(self.df.iloc[:, j]):
                    if is_invalid_cell(name):
                        invalid_cells.append(
                            self.content_invalid_cell_factory.create(i, j))
                continue

            if not self.__check_adjacent_columns(j, conditions):
                invalid_columns.append(
                    self.content_invalid_cell_factory.create(None, j))

        invalid_contents = []
        if len(invalid_cells):
            invalid_contents.append(
                InvalidContent("都道府県名は「都・道・府・県」まで正しく記入してください。", invalid_cells))
        if len(invalid_columns):
            invalid_contents.append(
                InvalidContent("都道府県コードを隣の列に併記する。もしくは、「都・道・府・県」まで正しく記入してください。",
                               invalid_columns))

        return LintResult(len(invalid_contents) == 0, invalid_contents)

    @before_check_1_1
    def check_1_13(self):
        """チェック項目1-13に沿って、数値データの同一列内に特殊記号（秘匿等）が含まれるか確認する。

        Note:
            数値データの同⼀列内に'0'、'X'、'***'以外の文字列が含まれる要素を invalid とみなす。
        """
        invalid_cells = []

        for j in range(len(self.df.columns)):
            column = self.df.iloc[:, j]
            if self.column_classify[j].is_number():
                for i, elem in enumerate(column):
                    # ex.1000円のようなケースはcheck_1_3でチェックするためスルー
                    if is_include_number(elem):
                        continue
                    if elem not in ["***", "X", "0"]:
                        invalid_cells.append(
                            self.content_invalid_cell_factory.create(i, j))

        return LintResult.gen_single_error_message_result(
            "数値データの列の空欄には'***','X','0'のいずれかを適切に入力してください。", invalid_cells)

    @before_check_1_1
    def check_2_x(self):
        """チェック項目2-1，2-2に沿って，データが分断されていないか，1シートに複数の表が掲載されていないか確認する。

        Note:
            データのない行または列がある場合 invalid とみなす。
        """
        column_results = self.df.isnull().all(axis=1)
        row_results = self.df.isnull().all()

        if column_results.sum() + row_results.sum():
            return LintResult.gen_simple_error_result(
                "データのない列や行が含まれている、もしくは複数の表が含まれています。")
        else:
            return LintResult(True, [])

    def __decode(self, data: bytes) -> str:
        self.encoding = chardet.detect(data)['encoding']
        self.encoding = 'utf-8' if self.encoding is None else self.encoding
        return data.decode(encoding=self.encoding)

    def __check_adjacent_columns(
            self, column_i: int,
            conditions: List[AdjacentColumnCondition]) -> bool:
        """隣接する左右の列が条件を満たしているかを確認。

        Args:
            column_i: 隣接を確認する対象の列のindex。
            conditions: 確認する条件のリスト。

        Returns:
            条件を満たす列が存在する場合にTrue、それ以外はFalse。
        """
        def check_adjacent_column(target_i: int, adjacent_i: int,
                                  condition: AdjacentColumnCondition) -> bool:
            if condition.type != self.column_classify[adjacent_i]:
                return False

            for target, adjacent in zip(self.df.iloc[:, target_i],
                                        self.df.iloc[:, adjacent_i]):
                if not condition.predicate(target, adjacent):
                    return False
            return True

        if column_i > 0 and any(
                map(partial(check_adjacent_column, column_i, column_i - 1),
                    conditions)):
            return True
        if column_i + 1 < len(self.df.columns) and any(
                map(partial(check_adjacent_column, column_i, column_i + 1),
                    conditions)):
            return True
        return False
