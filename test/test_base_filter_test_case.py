"""
Tests for the BaseFilterTestCase helper.
"""

from collections.abc import Mapping, Sequence
from unittest import TestCase

import pytest

import filters as f
from filters.test import BaseFilterTestCase


class RequiredTestCase(BaseFilterTestCase):
    """
    Concrete test case for exercising :py:meth:`assertFilterErrors`.
    """

    # Keeps pytest from collecting this helper as a test of its own.
    __test__ = False

    filter_type = f.Required

    def runTest(self) -> None:
        """
        Satisfies :py:class:`TestCase`, which needs a test method to
        instantiate.
        """


def run_assert_filter_errors(
    expected_codes: Mapping[str, Sequence[str]] | Sequence[str],
) -> None:
    """
    Runs :py:meth:`assertFilterErrors` on a value that
    :py:class:`f.Required` rejects as empty.
    """
    RequiredTestCase().assertFilterErrors(None, expected_codes)


@pytest.mark.parametrize(
    "expected_codes",
    [
        [f.Required.CODE_EMPTY],
        (f.Required.CODE_EMPTY,),
        {"": [f.Required.CODE_EMPTY]},
        {"": (f.Required.CODE_EMPTY,)},
    ],
)
def test_base_filter_test_case_assert_filter_errors_accepts_sequence(
    expected_codes: Mapping[str, Sequence[str]] | Sequence[str],
) -> None:
    """
    Any sequence of codes matches, not only a ``list``, at the top level
    or as a mapping's value.
    """
    run_assert_filter_errors(expected_codes)


def test_base_filter_test_case_assert_filter_errors_fails_on_wrong_codes() -> None:
    """
    Converting the expected codes does not make a mismatch pass.
    """
    with pytest.raises(TestCase.failureException):
        run_assert_filter_errors((f.Required.CODE_EMPTY, f.Required.CODE_EMPTY))


@pytest.mark.parametrize(
    "expected_codes",
    [
        f.Required.CODE_EMPTY,
        {"": f.Required.CODE_EMPTY},
    ],
)
def test_base_filter_test_case_assert_filter_errors_rejects_bare_str(
    expected_codes: Mapping[str, Sequence[str]] | Sequence[str],
) -> None:
    """
    A bare ``str`` raises rather than splitting into one code per
    character.
    """
    with pytest.raises(TypeError, match="single str"):
        run_assert_filter_errors(expected_codes)
