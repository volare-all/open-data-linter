import os
import pytest

import pandas as pd

from opendatalinter.column_classifier import ColumnType, ColumnClassifier


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
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "./samples/classify_sample.csv")
    with open(file_path, "r") as f:
        df = pd.read_csv(f, header=0)
    classifier = ColumnClassifier(df)

    column_types = classifier.perform()
    assert column_types[column] == expected_type
