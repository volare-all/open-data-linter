import unittest

from opendatalinter import CSVLinter, ExcelLinter
from opendatalinter.vo import LintResult
from opendatalinter.column_classifier import ColumnType


def gen_csv_linter(file_path: str) -> CSVLinter:
    with open(file_path, "rb") as f:
        return CSVLinter(f.read(), file_path)


def gen_excel_linter(file_path: str) -> ExcelLinter:
    with open(file_path, "rb") as f:
        return ExcelLinter(f.read(), file_path)


class TestCsvLinter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nb01h0013 = gen_csv_linter("samples/nb01h0013.csv")
        cls.nb01h0013_sjis = gen_csv_linter("samples/nb01h0013_sjis.csv")
        cls.nb01h0013_cp932 = gen_csv_linter("samples/nb01h0013_cp932.csv")
        cls.perfect = gen_csv_linter("samples/perfect.csv")
        cls.text = gen_csv_linter("samples/text.txt")
        cls.check_1_2 = gen_csv_linter("samples/check_1_2.csv")
        cls.classify_sample = gen_csv_linter("samples/classify_sample.csv")

    def test_empty_header(self):
        linter = gen_csv_linter("samples/all_num.csv")
        self.assertValidLintResult(linter.check_1_1())
        self.assertValidLintResult(linter.check_1_2())
        self.assertValidLintResult(linter.check_1_3())
        self.assertValidLintResult(linter.check_1_5())
        self.assertValidLintResult(linter.check_1_6())
        self.assertValidLintResult(linter.check_1_10())
        self.assertValidLintResult(linter.check_1_11())
        self.assertValidLintResult(linter.check_1_12())
        self.assertValidLintResult(linter.check_1_13())
        self.assertValidLintResult(linter.check_2_1())

    def test_check_1_1(self):
        self.assertTrue(self.nb01h0013.check_1_1().is_valid)
        self.assertFalse(self.text.check_1_1().is_valid)
        self.assertValidLintResult(self.perfect.check_1_1())

    def test_check_1_2(self):
        self.assertTrue(self.nb01h0013.check_1_2().is_valid)
        self.assertValidLintResult(self.perfect.check_1_2())
        res = self.check_1_2.check_1_2()
        self.assertFalse(res.is_valid)
        invalid_cells = []
        for ic in res.invalid_contents:
            invalid_cells.extend(ic.invalid_cells)
        invalid_cells = set(invalid_cells)
        self.assertEqual(
            {(1, 1), (2, 1), (3, 1), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3)},
            invalid_cells)

    def test_check_1_3(self):
        self.assertValidLintResult(self.perfect.check_1_3())
        linter = gen_csv_linter("samples/check_1_3.csv")
        result = linter.check_1_3()
        self.assertEqual({(4, 0), (5, 0), (6, 0), (7, 0), (9, 0), (7, 4)},
                         set(result.invalid_contents[0].invalid_cells))

    def test_check_1_5(self):
        self.assertValidLintResult(self.perfect.check_1_5())
        linter = gen_csv_linter("samples/check_1_5.csv")
        result = linter.check_1_5()
        self.assertEqual({(0, 2), (1, 1), (1, 2), (2, 0), (2, 1)},
                         set(result.invalid_contents[0].invalid_cells))

    def test_check_1_6(self):
        self.assertValidLintResult(self.perfect.check_1_6())
        linter = gen_csv_linter("samples/check_1_6.csv")
        result = linter.check_1_6()
        self.assertEqual(
            {(2, 0), (2, 3), (2, 4), (2, 6), (2, 7), (2, 9), (2, 10), (2, 12),
             (2, 13), (2, 14), (2, 16), (2, 17), (2, 18), (3, 0), (3, 18),
             (2, 19)}, set(result.invalid_contents[0].invalid_cells))

    def test_check_1_10(self):
        self.assertTrue(self.nb01h0013.check_1_10().is_valid)
        self.assertTrue(self.nb01h0013_sjis.check_1_10().is_valid)
        self.assertValidLintResult(self.perfect.check_1_10())
        res = self.nb01h0013_cp932.check_1_10()
        self.assertFalse(res.is_valid)
        self.assertEqual(1, len(res.invalid_contents))
        self.assertEqual(1, len(res.invalid_contents[0].invalid_cells))
        self.assertEqual((4, 0), res.invalid_contents[0].invalid_cells[0])

    def test_check_1_11(self):
        self.assertValidLintResult(self.perfect.check_1_11())
        linter = gen_csv_linter("samples/check_1_11.csv")
        result = linter.check_1_11()
        self.assertEqual({(1, 5), (2, 1), (2, 2), (2, 5)},
                         set(result.invalid_contents[0].invalid_cells))

    def test_check_1_12(self):
        self.assertValidLintResult(self.perfect.check_1_12())
        linter = gen_csv_linter("samples/check_1_12.csv")
        result = linter.check_1_12()

        self.assertSetEqual(set(result.invalid_contents[0].invalid_cells),
                            {(3, 5), (4, 5), (5, 5), (7, 5)})

        self.assertSetEqual(set(result.invalid_contents[1].invalid_cells),
                            {(None, 8)})

    def test_check_1_13(self):
        self.assertValidLintResult(self.perfect.check_1_12())
        linter = gen_csv_linter("samples/check_1_13.csv")
        result = linter.check_1_13()
        print(result)
        self.assertSetEqual({(2, 0), (2, 2), (3, 0), (3, 2), (3, 3)},
                            set(result.invalid_contents[0].invalid_cells))

    def test_check_2_1(self):
        self.assertValidLintResult(self.perfect.check_2_1())
        linter = gen_csv_linter("samples/check_2_1.csv")
        result = linter.check_2_1()
        self.assertEqual({(None, 18)},
                         set(result.invalid_contents[0].invalid_cells))
        self.assertEqual({(22, None)},
                         set(result.invalid_contents[1].invalid_cells))

    def assertValidLintResult(self, result: LintResult):
        self.assertTrue(result.is_valid)
        self.assertEqual(0, len(result.invalid_contents))

    def test_column_classify(self):

        linter = gen_csv_linter("samples/classify_sample.csv")
        classify_array = linter.column_classify
        self.assertEqual(classify_array[0], ColumnType.PREFECTURE_CODE)
        self.assertEqual(classify_array[2], ColumnType.PREFECTURE_NAME)
        self.assertEqual(classify_array[4], ColumnType.CHRISTIAN_ERA)
        self.assertEqual(classify_array[6], ColumnType.DATETIME_CODE)
        self.assertEqual(classify_array[8], ColumnType.JP_CALENDAR_YEAR)
        self.assertEqual(classify_array[10], ColumnType.OTHER_NUMBER)
        self.assertEqual(classify_array[12], ColumnType.OTHER_STRING)
        self.assertEqual(classify_array[14], ColumnType.NONE_CATEGORY)


class TestExcelLinter(unittest.TestCase):
    def test_check_1_1(self):
        linter = gen_excel_linter("./samples/since2003_visitor_arrivals.xlsx")
        self.assertTrue(linter.check_1_1().is_valid)

    def test_check_1_4(self):
        linter = gen_excel_linter("./samples/since2003_visitor_arrivals.xlsx")
        result = linter.check_1_4()
        self.assertFalse(result.is_valid)
        expected = []
        for i in range(3, 18):
            expected.append((i, 0))
        for i in range(21, 57):
            expected.append((i, 0))
        self.assertSetEqual(set(expected),
                            set(result.invalid_contents[0].invalid_cells))

    def test_check_1_7(self):
        linter = gen_excel_linter("samples/expression.xlsx")
        result = linter.check_1_7()
        self.assertEqual({(1, 2), (2, 0), (2, 2)},
                         set(result.invalid_contents[0].invalid_cells))


if __name__ == '__main__':
    unittest.main()
