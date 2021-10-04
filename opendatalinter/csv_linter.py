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
    VALID_PREFECTURE_NAME,
    INVALID_PREFECTURE_NAME,
)
from .vo import LintResult, InvalidContent, InvalidCellFactory
from .column_classifier import ColumnClassifier, ColumnType


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
        正確な地域名称が表記されている．もしくは，隣接するセルに都道府県コードが併記されているか
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

        # 都道府県名に該当するセルのうち，該当する全てのセルで都道府県の省略されている．かつ，隣接する列に完全一致する都道府県コードがある場合True
        def is_valid_prefecture_with_prefecture_code(name_c_index,
                                                     number_c_index):
            prefecture_name_column = self.df.iloc[:, name_c_index]
            prefecture_code_column = self.df.iloc[:, number_c_index]

            for name, number in zip(prefecture_name_column,
                                    prefecture_code_column):
                if is_empty(name):
                    continue

                if name == '北海道' and str(number) == '1':
                    continue

                # 正しい都道府県名が存在する場合，記法が統一されていないためFalse
                if name in VALID_PREFECTURE_NAME:
                    return False

                # 省略された都道府県名の隣のセルの都道府県コードが一致しない場合False
                if name in INVALID_PREFECTURE_NAME and str(
                        prefectures_numbers[name]) != str(number):
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

        invalid_cells = []
        invalid_columns = []

        # 都道府県名に分類される列ごとに判定
        for j in range(len(self.df.columns)):
            if not self.column_classify[j] == ColumnType.PREFECTURE_NAME:
                continue

            # 都道府県名に該当するセルのうち，完全な都道府県名で列が構成されている場合valid
            if is_valid_prefecture_name_column(j):
                continue

            # 都道府県名に該当するセルのうち，該当する全てのセルで都道府県の省略されている．かつ，左に隣接する列に完全一致する都道府県コードがある場合valid
            if j > 0 and self.column_classify[j -
                                              1] == ColumnType.PREFECTURE_CODE:
                if is_valid_prefecture_with_prefecture_code(j, j - 1):
                    continue

            # 都道府県名に該当するセルのうち，該当する全てのセルで都道府県の省略されている．かつ，右に隣接する列に完全一致する都道府県コードがある場合valid
            if j + 1 < len(self.df.columns) and self.column_classify[
                    j + 1] == ColumnType.PREFECTURE_CODE:
                if is_valid_prefecture_with_prefecture_code(j, j + 1):
                    continue

            # 都道府県名に該当するセルのうち，該当する全てのセルで都道府県名が省略されている．かつ，完全一致する都道府県番号が存在しない場合列単位でinvalid
            if is_invalid_column(j):
                invalid_columns.append(
                    self.content_invalid_cell_factory.create(None, j))
                continue

            # 都道府県名に該当するセルのうち，該当するセルごとに省略された都道府県名をinvalidとする処理
            for i, name in enumerate(self.df.iloc[:, j]):
                if is_invalid_cell(name):
                    invalid_cells.append(
                        self.content_invalid_cell_factory.create(i, j))

        invalid_contents = []
        if len(invalid_cells):
            invalid_contents.append(
                InvalidContent("都道府県名は「都・道・府・県」まで正しく記入してください", invalid_cells))
        if len(invalid_columns):
            invalid_contents.append(
                InvalidContent("都道府県コードを隣の列に併記する．もしくは，「都・道・府・県」まで正しく記入してください",
                               invalid_columns))

        return LintResult(len(invalid_contents) == 0, invalid_contents)

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
