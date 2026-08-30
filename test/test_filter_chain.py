"""
Tests for the FilterChain filter.
"""

import filters as f
import pytest


def test_filter_chain_implicit_chain(assert_filter_passes, assert_filter_errors):
    """
    Chaining two filters together creates a FilterChain.
    """
    filter_instance = f.Int | f.Max(3)

    assert_filter_passes(filter_instance, "1", 1)
    assert_filter_errors(filter_instance, "4", [f.Max.CODE_TOO_BIG])


def test_filter_chain_rejects_none():
    """
    Chaining a filter with ``None`` raises, whichever side of the
    operator the chain is on.

    This used to be a silent no-op. See
    docs/adr/009-drop-none-as-an-operand-of-the-chaining-operator.md.
    """
    with pytest.raises(TypeError):
        f.Int() | None

    with pytest.raises(TypeError):
        f.Int | None

    with pytest.raises(TypeError):
        (f.Int() | f.Max(3)) | None


def test_filter_chain_still_accepts_none_as_a_start_filter():
    """
    Only ``|`` rejects ``None``; ``FilterChain``'s own initialiser still
    treats it as "no filter yet", which is what ``FilterMapper`` and
    ``FilterSwitch`` rely on.
    """
    filter_chain = f.FilterChain(None)
    assert isinstance(filter_chain, f.FilterChain)
    assert filter_chain.apply("not an int") == "not an int"


# noinspection SpellCheckingInspection
def test_filter_chain_chainception(assert_filter_passes, assert_filter_errors):
    """
    You can also chain FilterChains together.
    """
    fc1 = f.NotEmpty | f.Choice(choices=("Lucky", "Dusty", "Ned"))
    fc2 = f.NotEmpty | f.MinLength(4)

    filter_instance = fc1 | fc2

    assert_filter_passes(filter_instance, "Lucky")
    assert_filter_errors(filter_instance, "El Guapo", [f.Choice.CODE_INVALID])
    assert_filter_errors(filter_instance, "Ned", [f.MinLength.CODE_TOO_SHORT])


def test_filter_chain_stop_after_invalid_value(assert_filter_errors):
    """
    A FilterChain stops processing the incoming value after any
    filter fails.
    """
    # This FilterChain will pretty much reject anything that you
    # throw at it.
    filter_instance = f.MaxLength(3) | f.MinLength(8) | f.Required

    # Note that the value 'foobar' fails both the MaxLength and the
    # MinLength filters, but the FilterChain stops processing
    # after MaxLength fails.
    assert_filter_errors(filter_instance, "foobar", [f.MaxLength.CODE_TOO_LONG])
