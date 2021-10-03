import os
import re
import traceback
from typing import List

import chardet
import numpy as np
from jeraconv import jeraconv

from .csv_structure_analyzer import CSVStructureAnalyzer
from .errors import HeaderEstimateError
from .funcs import (
    before_check_1_1,
    is_number,
    is_empty,
    is_include_number,
    is_jp_calendar_year,
    is_valid_date,
)
from .regex import (
    SPACES_AND_LINE_BREAK_REGEX,
    DATETIME_CODE_REGEX,
    CHRISTIAN_ERA_REGEX,
    NUM_WITH_BRACKETS_REGEX,
    NUM_WITH_NUM_REGEX,
)
from .vo import LintResult, InvalidContent, InvalidCellFactory
from .column_classifer import ColumnClassifer, ColumnType


class CSVLinter:
    INTEGER_RATE = 0.8  # 列を数値列か判定する基準(数値が含まれているセル数 / 列の長さ)
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
                "csv形式のファイルを用意してください。")
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
            self.column_classify = ColumnClassifer(
                self.df, self.CLASSIFY_RATE).perform(jeraconv.J2W())
            self.is_num_per_row = self.calc_is_num_per_row()
            print(self.is_num_per_row)
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
        """
        ファイル形式は Excel か CSV となっているか
        """
        if "1-1" not in self.cache:
            self.cache["1-1"] = LintResult(True, [])
        return self.cache["1-1"]

    @before_check_1_1
    def check_1_2(self):
        """
        １セル１データとなっているか
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
                InvalidContent("句点によりデータが分割されています",
                               comma_separated_invalid_cells))
        if len(num_with_brackets_invalid_cells):
            invalid_contents.append(
                InvalidContent("括弧によりデータが分割されています",
                               num_with_brackets_invalid_cells))

        return LintResult(not (bool(len(invalid_contents))), invalid_contents)

    @before_check_1_1
    def check_1_3(self):
        """
        数値データは数値属性とし、⽂字列を含まないこと
        """
        # 列ごとにループを回す
        # セル内に数値が含まれていたら「数値」とみなす
        # これに単位（文字列）があるとerrorに追加
        invalid_cells = []

        for i in range(len(self.df.columns)):
            column = self.df.iloc[:, i]
            if self.is_num_per_row[i]:
                for j, elem in enumerate(column):
                    if is_number(elem):
                        continue
                    if is_include_number(elem):
                        invalid_cells.append(
                            self.content_invalid_cell_factory.create(j, i))

        print(invalid_cells)

        return LintResult.gen_single_error_message_result(
            "数値データに文字が含まれています", invalid_cells)

    @before_check_1_1
    def check_1_5(self):
        """
        スペースや改⾏等で体裁を整えていないか。
        スペースと改行を1つ以上含む要素をinvalidとみなす。
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
            "スペースや改⾏が含まれています", invalid_cells)

    @before_check_1_1
    def check_1_6(self):
        """
        項⽬名等を省略していないか(ヘッダに欠損データがないか)
        """
        invalid_cells = list(
            map(lambda t: self.header_invalid_cell_factory.create(t[0], t[1]),
                np.argwhere(self.header_df.isnull().values)))
        return LintResult.gen_single_error_message_result(
            "ヘッダーに空欄があります", invalid_cells)

    @before_check_1_1
    def check_1_10(self):
        """
        機種依存⽂字を使⽤していないか。
        入力ファイルのエンコードがCP932かつshift_jisにデコードできない要素をinvalidとみなす。
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
                "機種依存⽂字が含まれています", invalid_cells)

        return LintResult(True, [])

    def __can_encode_from_cp932_to_sjis(self, text: str) -> bool:
        try:
            text.encode(encoding="CP932").decode("shift_jis")
            return True
        except UnicodeDecodeError:
            return False

    @before_check_1_1
    def check_1_11(self):
        """
        e-Stat の時間軸コードの表記、⻄暦表記⼜は和暦に⻄暦の併記がされているか
        """
        def is_valid_cell(cell: str, year: int) -> bool:
            is_valid_for_datetime_code = is_valid_date(cell,
                                                       DATETIME_CODE_REGEX,
                                                       year)
            is_valid_for_christian_era = is_valid_date(cell,
                                                       CHRISTIAN_ERA_REGEX,
                                                       year)
            return is_valid_for_datetime_code or is_valid_for_christian_era

        j2w = jeraconv.J2W()
        invalid_cells = []
        for column in self.__get_jp_calendar_column_indices(j2w):
            for row in range(len(self.df)):
                target_year = j2w.convert(str(self.df.at[row, column]))
                is_valid = False
                if column > 0:
                    left_cell = str(self.df[column - 1][row])
                    is_valid = is_valid or is_valid_cell(
                        left_cell, target_year)
                if column < len(self.df.columns) - 1:
                    right_cell = str(self.df[column + 1][row])
                    is_valid = is_valid or is_valid_cell(
                        right_cell, target_year)

                if not is_valid:
                    invalid_cells.append(
                        self.content_invalid_cell_factory.create(row, column))

        return LintResult.gen_single_error_message_result(
            "和暦に適切な時間軸コードまたは⻄暦が併記されていません", invalid_cells)

    def __get_jp_calendar_column_indices(self, j2w: jeraconv.J2W) -> List[int]:
        is_jp_calendar_columns = self.df \
            .applymap(lambda cell: is_jp_calendar_year(j2w, str(cell))) \
            .all(axis=0)
        return np.squeeze(np.argwhere(is_jp_calendar_columns.values),
                          axis=1).tolist()

    @before_check_1_1
    def check_1_12(self):
        """
        地域コード⼜は地域名称が表記されているか（都道府県名の表記揺れ）
        """
        invalid_prefectures = [
            '青森', '岩手', '宮城', '秋田', '山形', '福島', '茨城', '栃木', '群馬', '埼玉', '千葉',
            '東京', '神奈川', '新潟', '富山', '石川', '福井', '山梨', '長野', '岐阜', '静岡', '愛知',
            '三重', '滋賀', '京都', '大阪', '兵庫', '奈良', '和歌山', '鳥取', '島根', '岡山', '広島',
            '山口', '徳島', '香川', '愛媛', '高知', '福岡', '佐賀', '長崎', '熊本', '大分', '宮崎',
            '鹿児島', '沖縄'
        ]

        prefectures_numbers = {
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

        invalid_cells = []

        for j in range(len(self.df.columns)):
            column = self.df.iloc[:, j]
            for i, elem in enumerate(column):
                if elem in invalid_prefectures:
                    print(f"elem: {elem}")
                    # 両隣に都道府県コードと一致する数字がない場合警告に追加する
                    if j > 0:
                        left_elem = self.df.iat[i, j - 1]
                        if left_elem == prefectures_numbers[elem]:
                            continue
                        if type(left_elem) is str:
                            if is_number(left_elem):
                                float_left_elem = float(left_elem)
                                if float_left_elem.is_integer() and int(
                                        float_left_elem
                                ) == prefectures_numbers[elem]:
                                    continue

                    if j + 1 < len(self.df.columns):
                        right_elem = self.df.iat[i, j + 1]
                        if right_elem == prefectures_numbers[elem]:
                            continue
                        if type(right_elem) is str:
                            if is_number(right_elem):
                                float_right_elem = float(right_elem)
                                if float_right_elem.is_integer() and int(
                                        float_right_elem
                                ) == prefectures_numbers[elem]:
                                    continue
                    invalid_cells.append(
                        self.content_invalid_cell_factory.create(i, j))

        return LintResult.gen_single_error_message_result(
            "地域名称が正しく表記されていません．", invalid_cells)

    @before_check_1_1
    def check_1_13(self):
        """
        数値データの同⼀列内に特殊記号（秘匿等）が含まれる場合
        """
        # 列ごとにループを回す
        # 列が数値データであることを確認する
        # dtypeがintならstringになりうるセルがないのでTrueを返して終了する
        invalid_cells = []

        for i in range(len(self.df.columns)):
            column = self.df.iloc[:, i]
            if self.is_num_per_row[i]:
                for j, elem in enumerate(column):
                    if is_number(elem):
                        continue
                    if is_empty(elem):
                        if elem == "***":
                            continue
                        invalid_cells.append(
                            self.content_invalid_cell_factory.create(j, i))

        return LintResult.gen_single_error_message_result(
            "空の数値データに適切な記号が入っていません．", invalid_cells)

    @before_check_1_1
    def check_2_1(self):
        """
        データが分断されていないか
        """
        invalid_row_cells = []
        invalid_column_cells = []

        # データがない列がないか確認する
        results = self.df.isnull().all(axis=1)
        for i, result in enumerate(results):
            if result:
                invalid_column_cells.append(
                    self.content_invalid_cell_factory.create(i, None))

        # データがない行がないか確認する
        results = self.df.isnull().all()
        for i, result in enumerate(results):
            if result:
                invalid_row_cells.append(
                    self.content_invalid_cell_factory.create(None, i))

        invalid_contents = []
        if len(invalid_row_cells):
            invalid_contents.append(
                InvalidContent("データが入っていない列が入っています.", invalid_row_cells))
        if len(invalid_column_cells):
            invalid_contents.append(
                InvalidContent("データが入っていない行が入っています.", invalid_column_cells))

        return LintResult(
            len(invalid_row_cells) + len(invalid_column_cells) == 0,
            invalid_contents)

    def calc_is_num_per_row(self):
        """
        返り値: [配列]列ごとの数値列であるかの真偽値

        数値列の定義：数値が含まれているセルが全体の`INTEGER_RATE`以上の割合を占める
        """

        array = []
        for i in range(len(self.df.columns)):
            column = self.df.iloc[:, i]
            integer_count = 0
            empty_count = 0
            for elem in column:
                # print(f"\t\t{integer_count}")
                # print(f"\t + {elem}")

                if is_empty(elem):
                    empty_count += 1
                    continue

                if is_number(elem):
                    integer_count += 1
                    continue

                if is_include_number(elem):
                    integer_count += 1
                    continue

            # print(f"integer_count: {integer_count}")
            # print(f"empty_count: {empty_count}")
            # print(f"len(df): {len(self.df)}")
            try:
                if (integer_count /
                    (len(self.df) - empty_count)) > self.INTEGER_RATE:
                    array.append(True)
                else:
                    array.append(False)
            except ZeroDivisionError:
                array.append(False)
        return array

    def __decode(self, data: bytes) -> str:
        self.encoding = chardet.detect(data)['encoding']
        self.encoding = 'utf-8' if self.encoding is None else self.encoding
        return data.decode(encoding=self.encoding)
