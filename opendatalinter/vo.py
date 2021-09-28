from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class InvalidContent:
    error_message: str
    invalid_cells: List[Tuple[Optional[int], Optional[int]]]

    def to_dict(self):
        return {
            "error_message": self.error_message,
            "invalid_cells": self.invalid_cells
        }


@dataclass
class LintResult:
    is_valid: Optional[bool]
    invalid_contents: List[InvalidContent]

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "invalid_contents": [c.to_dict() for c in self.invalid_contents]
        }

    @classmethod
    def gen_simple_error_result(cls,
                                error_message: str,
                                is_valid: Optional[bool] = False):
        return LintResult(is_valid, [InvalidContent(error_message, [])])

    @staticmethod
    def gen_single_error_message_result(
            error_message: str, invalid_cells: List[Tuple[Optional[int],
                                                          Optional[int]]]):
        is_valid = len(invalid_cells) == 0
        return LintResult(
            is_valid,
            [] if is_valid else [InvalidContent(error_message, invalid_cells)])


class InvalidCellFactory:
    def __init__(self, row_offset):
        self.row_offset = row_offset

    def create(self, i, j):
        if i is not None:
            i += self.row_offset
        return i, j
