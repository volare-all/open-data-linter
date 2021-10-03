import csv
from io import StringIO
from typing import List

import numpy as np
import pandas as pd
from pandas import DataFrame

from .errors import HeaderEstimateError
from .funcs import is_number


class CSVStructureAnalyzer:
    def __init__(self, text: str, should_print_info: bool = False):
        reader = csv.reader(StringIO(text))
        self.__rows = list(reader)
        self.__row_element_counts = list(map(len, self.__rows))
        self.__row_count = len(self.__row_element_counts)

        self.__content_range = self.__estimate_content_range()
        self.title_line_num = self.__content_range[0]
        self.header_line_num = self.__estimate_header_line_num()

        if should_print_info:
            self.__print_debug_info()

    def gen_header_df(self) -> DataFrame:
        if self.header_line_num == 0:
            return pd.DataFrame(np.empty(0))

        return pd.read_csv(StringIO(self.__get_header()), header=None)

    def gen_rows_df(self) -> DataFrame:
        return pd.read_csv(StringIO(self.__get_rows()), header=None)

    # def __estimate_content_range(self) -> tuple[int, int]:
    def __estimate_content_range(self):
        """
        行ごとにカンマで区切られた要素の数を計算し、同じ数が最も連続している部分をContentと判別
        :return: Contentが含まれる行のレンジ(inclusive, exclusive)
        """
        consecutive_counts: List[int] = []
        count = 0
        for i in range(self.__row_count):
            if i == self.__row_count - 1 or self.__row_element_counts[
                    i] == self.__row_element_counts[i + 1]:
                count += 1
                continue

            consecutive_counts.append(count + 1)
            count = 0
        consecutive_counts.append(count)

        max_count = max(consecutive_counts)
        start_index = 0
        for c in consecutive_counts:
            if c == max_count:
                break
            start_index += c

        return start_index, start_index + max_count

    def __estimate_header_line_num(self):
        cr = self.__content_range
        for i, row in enumerate(self.__rows[cr[0]:cr[1]]):
            for element in row:
                if is_number(element):
                    return i
        # TODO: Headerが存在しないケースも検討する
        raise HeaderEstimateError()

    def __print_debug_info(self):
        lines = list(map(self.__to_line, self.__rows))
        print(f"========== Title([0, {self.title_line_num})) ==========")
        print("\n".join(lines[:self.title_line_num]))

        header_end = self.title_line_num + self.header_line_num
        print(
            f"========== Header([{self.title_line_num}, {header_end})) =========="
        )
        print(self.__get_header())

        rows_end = self.__content_range[1]
        print(f"========== Rows([{header_end}, {rows_end})) ==========")
        print(self.__get_rows())

    def __get_header(self):
        header_end = self.title_line_num + self.header_line_num
        header_lines = map(self.__to_line,
                           self.__rows[self.title_line_num:header_end])
        return "".join(header_lines)

    def __get_rows(self):
        cr = self.__content_range
        content_lines = map(self.__to_line,
                            self.__rows[cr[0] + self.header_line_num:cr[1]])
        return "".join(content_lines)

    @staticmethod
    def __to_line(row: List[str]):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(row)
        return output.getvalue()
