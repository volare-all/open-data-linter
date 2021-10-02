import csv
from io import StringIO
from typing import List


class CSVStructureAnalyzer:
    def __init__(self, text: str, should_print_info: bool = False):
        reader = csv.reader(StringIO(text))
        self.__rows = list(reader)
        self.__row_element_counts = list(map(len, self.__rows))
        self.__row_count = len(self.__row_element_counts)

        self.__content_range = self.__estimate_content_range()
        self.title_line_num = self.__content_range[0]

        if should_print_info:
            self.__print_debug_info()

    def __estimate_content_range(self) -> tuple[int, int]:
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

    def __print_debug_info(self):
        lines = list(map(self.__to_line, self.__rows))
        print("========== Title ==========")
        print("\n".join(lines[:self.title_line_num]))

    @staticmethod
    def __to_line(row: List[str]):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(row)
        return output.getvalue()
