"""
Tests for the Uuid filter.
"""

from uuid import UUID

import filters as f


def test_uuid_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | Uuid`` if you want to reject null values.
    """
    assert_filter_passes(f.Uuid(), None)


def test_uuid_pass_uuid_value(assert_filter_passes):
    """
    The incoming value can be interpreted as a UUID.
    """
    filtered = f.Uuid()
    runner = assert_filter_passes(
        filtered,
        "3466c56a-2ebc-449d-97d2-9b119721ff0f",
        UUID("3466c56a-2ebc-449d-97d2-9b119721ff0f"),
    )

    uuid = runner.cleaned_data
    assert isinstance(uuid, UUID)

    assert uuid.hex == "3466c56a2ebc449d97d29b119721ff0f"
    assert uuid.version == 4


def test_uuid_pass_hex(assert_filter_passes):
    """
    You can omit the dashes when specifying a UUID value.
    """
    filtered = f.Uuid()
    runner = assert_filter_passes(
        filtered,
        "3466c56a2ebc449d97d29b119721ff0f",
        UUID("3466c56a2ebc449d97d29b119721ff0f"),
    )

    uuid = runner.cleaned_data
    assert isinstance(uuid, UUID)

    assert uuid.hex == "3466c56a2ebc449d97d29b119721ff0f"
    assert uuid.version == 4


# noinspection SpellCheckingInspection
def test_uuid_pass_curly_hex(assert_filter_passes):
    """
    You can include curly braces around hex values.

    Use ``Regex(r'^[\\da-f]+$') | Uuid`` if you only want to allow plain
    hex.
    """
    filtered = f.Uuid()
    runner = assert_filter_passes(
        filtered,
        "{54d6ebf8a3f55ed59becdedfb3b0773f}",
        UUID("54d6ebf8a3f55ed59becdedfb3b0773f"),
    )

    uuid = runner.cleaned_data
    assert isinstance(uuid, UUID)

    assert uuid.hex == "54d6ebf8a3f55ed59becdedfb3b0773f"
    assert uuid.version == 5


def test_uuid_pass_urn(assert_filter_passes):
    """
    You can also specify a URN.  The term (and format) is somewhat
    antiquated, but still valid.

    If you want to prohibit URNs, chain this filter with
    ``Regex(r'^[\\da-f]+$')``.

    References:

      - https://en.wikipedia.org/wiki/Uniform_resource_name
    """
    filtered = f.Uuid()
    runner = assert_filter_passes(
        filtered,
        "urn:uuid:2830f705-5969-11e5-9628-e0f8470933c8",
        UUID("2830f705-5969-11e5-9628-e0f8470933c8"),
    )

    uuid = runner.cleaned_data
    assert isinstance(uuid, UUID)

    assert uuid.hex == "2830f705596911e59628e0f8470933c8"
    assert uuid.version == 1


def test_uuid_fail_wrong_version(assert_filter_errors):
    """
    Configuring the filter to only accept a specific UUID version.
    """
    assert_filter_errors(
        # Incoming value is a v1 UUID, but we're expecting a v4.
        f.Uuid(version=4),
        "2830f705596911e59628e0f8470933c8",
        [f.Uuid.CODE_WRONG_VERSION],
    )


def test_uuid_fail_int(assert_filter_errors):
    """
    The incoming value must be a HEX representation of a UUID. Decimal
    values are not valid.
    """
    assert_filter_errors(
        f.Uuid(),
        "306707680894066278898485957190279549189",
        [f.Uuid.CODE_INVALID],
    )


def test_uuid_fail_wrong_type(assert_filter_errors):
    """
    Attempting to filter anything other than a string value fails rather
    spectacularly.
    """
    assert_filter_errors(
        f.Uuid(),
        [
            "e6bdc02c9d004991986d3c7c0730d105",
            "2830f705596911e59628e0f8470933c8",
        ],
        [f.Type.CODE_WRONG_TYPE],
    )


def test_uuid_pass_uuid_object(assert_filter_passes):
    """
    The incoming value is already a UUID object.
    """
    assert_filter_passes(f.Uuid(), UUID("e6bdc02c9d004991986d3c7c0730d105"))


def test_uuid_fail_uuid_object_wrong_version(assert_filter_errors):
    """
    The incoming value is already a UUID object, but its version doesn't
    match the expected one.
    """
    # noinspection SpellCheckingInspection
    assert_filter_errors(
        # Incoming value is a v5 UUID, but we're expecting a v4.
        f.Uuid(version=4),
        UUID("54d6ebf8a3f55ed59becdedfb3b0773f"),
        [f.Uuid.CODE_WRONG_VERSION],
    )
