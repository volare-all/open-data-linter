import os

from opendatalinter import CSVLinter, ExcelLinter
from opendatalinter.vo import LintResult


def gen_csv_linter(file_path: str) -> CSVLinter:
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             file_path)
    with open(file_path, "rb") as f:
        return CSVLinter(f.read(), file_path)


def gen_excel_linter(file_path: str) -> ExcelLinter:
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             file_path)
    with open(file_path, "rb") as f:
        return ExcelLinter(f.read(), file_path)


def assert_valid_lint_result(result: LintResult):
    assert result.is_valid
    assert len(result.invalid_contents) == 0


def assert_all_csv_check_is_valid(linter: CSVLinter):
    assert_valid_lint_result(linter.check_1_1())
    assert_valid_lint_result(linter.check_1_2())
    assert_valid_lint_result(linter.check_1_3())
    assert_valid_lint_result(linter.check_1_5())
    assert_valid_lint_result(linter.check_1_6())
    assert_valid_lint_result(linter.check_1_10())
    assert_valid_lint_result(linter.check_1_11())
    assert_valid_lint_result(linter.check_1_12())
    assert_valid_lint_result(linter.check_1_13())
    assert_valid_lint_result(linter.check_2_x())


def assert_all_excel_check_is_valid(linter: ExcelLinter):
    assert_valid_lint_result(linter.check_1_1())
    assert_valid_lint_result(linter.check_1_2())
    assert_valid_lint_result(linter.check_1_3())
    assert_valid_lint_result(linter.check_1_4())
    assert_valid_lint_result(linter.check_1_5())
    assert_valid_lint_result(linter.check_1_6())
    assert_valid_lint_result(linter.check_1_7())
    assert_valid_lint_result(linter.check_1_10())
    assert_valid_lint_result(linter.check_1_11())
    assert_valid_lint_result(linter.check_1_12())
    assert_valid_lint_result(linter.check_1_13())
    assert_valid_lint_result(linter.check_2_x())
