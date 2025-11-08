"""
Tests for the IpAddress filter.
"""

import filters as f


def test_ip_address_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | IpAddress`` if you want to reject null values.
    """
    assert_filter_passes(f.IpAddress(), None)


def test_ip_address_ipv4_success_happy_path(assert_filter_passes):
    """
    The incoming value is a valid IPv4 address.
    """
    assert_filter_passes(f.IpAddress(), "127.0.0.1")


def test_ip_address_ipv4_error_invalid(assert_filter_errors):
    """
    The incoming value is not a valid IPv4 address.
    """
    assert_filter_errors(f.IpAddress(), "127.0.0.1/32", [f.IpAddress.CODE_INVALID])
    assert_filter_errors(f.IpAddress(), "256.0.0.1", [f.IpAddress.CODE_INVALID])
    assert_filter_errors(f.IpAddress(), "-1.0.0.1", [f.IpAddress.CODE_INVALID])


def test_ip_address_ipv4_error_too_short(assert_filter_errors):
    """
    Technically, an IPv4 address can contain less than 4 octets, but this
    filter always expects exactly 4.
    """
    assert_filter_errors(f.IpAddress(), "127.1", [f.IpAddress.CODE_INVALID])


def test_ip_address_ipv4_error_too_long(assert_filter_errors):
    """
    The incoming value looks like an IPv4 address, except it contains too
    many octets.
    """
    assert_filter_errors(f.IpAddress(), "127.0.0.1.32", [f.IpAddress.CODE_INVALID])


def test_ip_address_ipv4_error_ipv6(assert_filter_errors):
    """
    By default, this filter does not accept IPv6 addresses.
    """
    assert_filter_errors(
        f.IpAddress(),
        "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        [f.IpAddress.CODE_INVALID],
    )


def test_ip_address_ipv6_success_happy_path(assert_filter_passes):
    """
    The incoming value is a valid IPv6 address.
    """
    assert_filter_passes(
        f.IpAddress(
            # You must explicitly configure the filter to accept IPv6
            # addresses.
            ipv4=False,
            ipv6=True,
        ),
        "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        # Note that the resulting value is automatically abbreviated, if
        # possible.
        # https://en.wikipedia.org/wiki/IPv6_address#Presentation
        "2001:db8:85a3::8a2e:370:7334",
    )


def test_ip_address_ipv6_success_case_insensitive(assert_filter_passes):
    """
    The incoming value uses mixed case for hex characters.
    """
    assert_filter_passes(
        f.IpAddress(
            ipv4=False,
            ipv6=True,
        ),
        "2001:0DB8:85A3:0000:0000:8a2e:0370:7334",
        "2001:db8:85a3::8a2e:370:7334",
    )


def test_ip_address_ipv6_success_truncated_zeroes(assert_filter_passes):
    """
    IPv6 supports truncating leading zeroes.
    """
    assert_filter_passes(
        f.IpAddress(
            ipv4=False,
            ipv6=True,
        ),
        "2001:db8:85a3:0:0:8a2e:370:7334",
        "2001:db8:85a3::8a2e:370:7334",
    )


def test_ip_address_ipv6_success_truncated_groups(assert_filter_passes):
    """
    Empty groups (all zeroes) can be omitted entirely.
    """
    assert_filter_passes(
        f.IpAddress(
            ipv4=False,
            ipv6=True,
        ),
        "2001:db8:85a3::8a2e:370:7334",
    )


def test_ip_address_ipv6_success_dotted_quad(assert_filter_passes):
    """
    IPv6 supports "dotted quad" notation for IPv4 addresses that are
    mid-transition.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.IpAddress(ipv4=False, ipv6=True),
        "::ffff:192.0.2.128",
    )


def test_ip_address_ipv6_error_invalid(assert_filter_errors):
    """
    Invalid IPv6 address is invalid.
    """
    assert_filter_errors(
        f.IpAddress(ipv4=False, ipv6=True),
        "not even close",
        [f.IpAddress.CODE_INVALID],
    )


def test_ip_address_ipv6_error_too_long(assert_filter_errors):
    """
    If the incoming value has too many groups to be IPv6, it is invalid.
    """
    assert_filter_errors(
        f.IpAddress(
            ipv4=False,
            ipv6=True,
        ),
        # Oops; one group too many!
        "2001:0db8:85a3:0000:0000:8a2e:0370:7334:1234",
        [f.IpAddress.CODE_INVALID],
    )


def test_ip_address_ipv6_error_ipv4(assert_filter_errors):
    """
    If the filter is configured only to accept IPv6 addresses, IPv4
    addresses are invalid.
    """
    assert_filter_errors(
        f.IpAddress(ipv4=False, ipv6=True),
        "127.0.0.1",
        [f.IpAddress.CODE_INVALID],
    )


def test_ip_address_pass_allow_ipv4_and_ipv6(assert_filter_passes):
    """
    You can configure the filter to accept both IPv4 and IPv6 addresses.
    """
    assert_filter_passes(
        f.IpAddress(ipv4=True, ipv6=True),
        "127.0.0.1",
    )

    assert_filter_passes(
        f.IpAddress(
            ipv4=True,
            ipv6=True,
        ),
        "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        "2001:db8:85a3::8a2e:370:7334",
    )


def test_ip_address_fail_bytes(assert_filter_errors):
    """
    For backwards-compatibility with previous versions of the library, byte
    strings are not allowed.
    """
    assert_filter_errors(f.IpAddress(), b"127.0.0.1", [f.Type.CODE_WRONG_TYPE])


def test_ip_address_fail_wrong_type(assert_filter_errors):
    """
    The incoming value is not a string.
    """
    assert_filter_errors(
        f.IpAddress(),
        ["127.0.0.1", "192.168.1.1"],
        [f.Type.CODE_WRONG_TYPE],
    )
