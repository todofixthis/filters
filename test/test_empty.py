import filters as f
from .conftest import Lengthy


def test_empty_pass_none(assert_filter_passes):
    """
    ``None`` shall pass.

    What?

    ``None`` shall pass!
    """
    assert_filter_passes(f.Empty(), None)


def test_empty_pass_empty_string(assert_filter_passes):
    """
    The incoming value is an empty string.
    """
    assert_filter_passes(f.Empty(), "")


def test_empty_pass_empty_collection(assert_filter_passes):
    """
    The incoming value is a collection with length < 1.
    """
    assert_filter_passes(f.Empty(), [])
    assert_filter_passes(f.Empty(), {})
    assert_filter_passes(f.Empty(), Lengthy(0))
    # etc.


def test_empty_fail_non_empty_string(assert_filter_errors):
    """
    The incoming value is a non-empty string.
    """
    assert_filter_errors(
        f.Empty(),
        "Goodbye world!",
        [f.Empty.CODE_NOT_EMPTY],
    )


def test_empty_fail_non_empty_collection(assert_filter_errors):
    """
    The incoming value is a collection with length > 0.
    """
    # The values inside the collection may be empty, but the collection
    # itself is not.
    assert_filter_errors(f.Empty(), ["", "", ""], [f.Empty.CODE_NOT_EMPTY])
    assert_filter_errors(f.Empty(), {"": ""}, [f.Empty.CODE_NOT_EMPTY])
    assert_filter_errors(f.Empty(), Lengthy(1), [f.Empty.CODE_NOT_EMPTY])
    # etc.


def test_empty_fail_non_collection(assert_filter_errors):
    """
    The incoming value does not have a length.
    """
    # The filter can't determine the length of this object, so it assumes
    # that it is not empty.
    assert_filter_errors(f.Empty(), object(), [f.Empty.CODE_NOT_EMPTY])


def test_empty_zero_is_not_empty(assert_filter_errors):
    """
    PHP developers take note!
    """
    assert_filter_errors(f.Empty(), 0, [f.Empty.CODE_NOT_EMPTY])


def test_empty_false_is_not_empty(assert_filter_errors):
    """
    The boolean value ``False`` is NOT considered empty because it
    represents SOME kind of value.
    """
    assert_filter_errors(f.Empty(), False, [f.Empty.CODE_NOT_EMPTY])
