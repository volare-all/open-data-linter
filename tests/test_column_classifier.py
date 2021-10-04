import pandas as pd
import pytest
from jeraconv import jeraconv

from opendatalinter.column_classifer import ColumnClassifer, ColumnType


@pytest.mark.parametrize(('column', 'expected_type'), [
    (0, ColumnType.PREFECTURE_CODE),
    (2, ColumnType.PREFECTURE_NAME),
    (4, ColumnType.CHRISTIAN_ERA),
    (6, ColumnType.DATETIME_CODE),
    (8, ColumnType.JP_CALENDAR_YEAR),
    (10, ColumnType.OTHER_NUMBER),
    (12, ColumnType.OTHER_STRING),
    (14, ColumnType.NONE_CATEGORY),
])
def test_column_classify(column, expected_type):
    with open("./samples/classify_sample.csv", "r") as f:
        df = pd.read_csv(f, header=0)
    classifier = ColumnClassifer(df)

    column_types = classifier.perform(jeraconv.J2W())
    assert column_types[column] == expected_type
