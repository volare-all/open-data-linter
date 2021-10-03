import re

EMPTY_REGEX_LIST = list(
    map(lambda s: re.compile(s), [r'^\s*$', '-', 'ー', 'なし']))

SPACES_AND_LINE_BREAK_REGEX = re.compile(r'.*[\s\n].*')
DATETIME_CODE_REGEX = re.compile(r"^(\d{4})[01][012]\d{4}$")
CHRISTIAN_ERA_REGEX = re.compile(r"^(\d{1,4})年?$")
NUM_WITH_BRACKETS_REGEX = re.compile(r"^(\d+?)(\s*?)[\(（)](.+?)[\)）]")
NUM_WITH_NUM_REGEX = re.compile(r"^(\d+?)((\s+?)(\d+?))+?")
