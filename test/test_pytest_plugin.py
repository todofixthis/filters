"""Tests for the filters pytest plugin."""

import filters as f
import filters.pytest_plugin as plugin


def test_module_exports():
    """Plugin __all__ contains the expected public symbols."""
    assert "assert_filter_errors" in plugin.__all__
    assert "assert_filter_passes" in plugin.__all__
    assert "skip_value_check" in plugin.__all__
    assert "unmodified" in plugin.__all__


def test_unmodified_is_sentinel():
    """unmodified is a class, not an instance."""
    assert isinstance(plugin.unmodified, type)


def test_skip_value_check_is_sentinel():
    """skip_value_check is a class, not an instance."""
    assert isinstance(plugin.skip_value_check, type)


def test_assert_filter_passes_fixture(assert_filter_passes):
    """assert_filter_passes fixture is injected and functional."""
    assert_filter_passes(f.Int(), "42", 42)


def test_assert_filter_errors_fixture(assert_filter_errors):
    """assert_filter_errors fixture is injected and functional."""
    assert_filter_errors(f.Int(), "not-an-int", [f.Decimal.CODE_INVALID])
