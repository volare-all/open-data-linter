import pytest

from tests.util import gen_csv_linter, assert_valid_lint_result, assert_all_csv_check_is_valid


@pytest.fixture
def nb01h0013():
    return gen_csv_linter("./samples/nb01h0013.csv")


@pytest.fixture
def perfect():
    return gen_csv_linter("./samples/perfect.csv")


def test_empty_header():
    linter = gen_csv_linter("./samples/all_num.csv")
    assert_all_csv_check_is_valid(linter)


def test_check_1_1(nb01h0013, perfect):
    text = gen_csv_linter("./samples/text.txt")

    assert nb01h0013.check_1_1().is_valid
    assert not text.check_1_1().is_valid
    assert_valid_lint_result(perfect.check_1_1())


def test_check_1_2(nb01h0013, perfect):
    assert nb01h0013.check_1_2().is_valid
    assert_valid_lint_result(perfect.check_1_2())

    linter = gen_csv_linter("./samples/check_1_2.csv")
    res = linter.check_1_2()
    assert not res.is_valid
    invalid_cells = []
    for ic in res.invalid_contents:
        invalid_cells.extend(ic.invalid_cells)
    assert set(invalid_cells) == \
           {(1, 1), (2, 1), (3, 1), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3)}


def test_check_1_3(perfect):
    assert_valid_lint_result(perfect.check_1_3())

    linter = gen_csv_linter("./samples/check_1_3.csv")
    result = linter.check_1_3()
    assert set(result.invalid_contents[0].invalid_cells) == \
           {(7, 1), (8, 1)}
    assert set(result.invalid_contents[1].invalid_cells) == \
           {(None, 2), (None, 3)}


def test_check_1_5(perfect):
    assert_valid_lint_result(perfect.check_1_5())

    linter = gen_csv_linter("./samples/check_1_5.csv")
    result = linter.check_1_5()
    assert set(result.invalid_contents[0].invalid_cells) == \
           {(0, 2), (1, 1), (1, 2), (2, 0), (2, 1)}


def test_check_1_6(perfect):
    assert_valid_lint_result(perfect.check_1_6())

    linter = gen_csv_linter("./samples/check_1_6.csv")
    result = linter.check_1_6()
    assert set(result.invalid_contents[0].invalid_cells) == \
           {(2, 0), (2, 3), (2, 4), (2, 6), (2, 7), (2, 9),
            (2, 10), (2, 12), (2, 13), (2, 14), (2, 16),
            (2, 17), (2, 18), (3, 0), (3, 18), (2, 19)}


def test_check_1_10(nb01h0013, perfect):
    assert nb01h0013.check_1_10().is_valid
    assert_valid_lint_result(perfect.check_1_10())

    nb01h0013_sjis = gen_csv_linter("./samples/nb01h0013_sjis.csv")
    assert nb01h0013_sjis.check_1_10().is_valid

    nb01h0013_cp932 = gen_csv_linter("./samples/nb01h0013_cp932.csv")
    res = nb01h0013_cp932.check_1_10()
    assert not res.is_valid
    assert len(res.invalid_contents) == 1
    assert len(res.invalid_contents[0].invalid_cells) == 1
    assert res.invalid_contents[0].invalid_cells[0] == (4, 0)


def test_check_1_11(perfect):
    assert_valid_lint_result(perfect.check_1_11())

    linter = gen_csv_linter("./samples/check_1_11.csv")
    result = linter.check_1_11()
    assert set(result.invalid_contents[0].invalid_cells) == \
           {(None, 2), (None, 5)}


def test_check_1_12(perfect):
    assert_valid_lint_result(perfect.check_1_12())

    linter = gen_csv_linter("./samples/check_1_12.csv")
    result = linter.check_1_12()
    assert set(result.invalid_contents[0].invalid_cells) == \
           {(3, 5), (4, 5), (5, 5), (7, 5)}
    assert set(result.invalid_contents[1].invalid_cells) == {(None, 8)}


def test_check_1_13(perfect):
    assert_valid_lint_result(perfect.check_1_12())

    linter = gen_csv_linter("./samples/check_1_13.csv")
    result = linter.check_1_13()
    assert set(result.invalid_contents[0].invalid_cells) == \
           {(2, 0), (4, 0), (5, 0)}


def test_check_2_x(perfect):
    assert_valid_lint_result(perfect.check_2_x())

    linter = gen_csv_linter("./samples/check_2_1.csv")
    assert not linter.check_2_x().is_valid
