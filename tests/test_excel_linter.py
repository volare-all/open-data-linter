from opendatalinter import ExcelLinter


def gen_excel_linter(file_path: str) -> ExcelLinter:
    with open(file_path, "rb") as f:
        return ExcelLinter(f.read(), file_path)


def test_check_1_1():
    linter = gen_excel_linter("./samples/since2003_visitor_arrivals.xlsx")
    assert linter.check_1_1().is_valid


def test_check_1_4():
    linter = gen_excel_linter("./samples/since2003_visitor_arrivals.xlsx")
    result = linter.check_1_4()
    assert not result.is_valid
    expected = []
    for i in range(3, 18):
        expected.append((i, 0))
    for i in range(21, 57):
        expected.append((i, 0))
    assert set(result.invalid_contents[0].invalid_cells) == set(expected)


def test_check_1_7():
    linter = gen_excel_linter("./samples/expression.xlsx")
    result = linter.check_1_7()
    assert set(result.invalid_contents[0].invalid_cells) == \
           {(1, 2), (2, 0), (2, 2)}
