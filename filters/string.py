import json
import socket
import typing
import unicodedata
from base64 import standard_b64decode, urlsafe_b64decode
from decimal import Decimal as DecimalType
from itertools import zip_longest
from uuid import UUID
from xml.etree.ElementTree import Element, tostring

import regex

from filters.base import BaseFilter, Type
from filters.simple import MaxLength

__all__ = [
    'Base64Decode',
    'ByteString',
    'CaseFold',
    'Choice',
    'IpAddress',
    'JsonDecode',
    'MaxBytes',
    'Regex',
    'Split',
    'Strip',
    'Unicode',
    'Uuid',
]


class Base64Decode(BaseFilter):
    """
    Decodes an incoming value using the Base64 algo.
    """
    CODE_INVALID = 'not_base64'

    templates = {
        CODE_INVALID: 'Base64-encoded value expected.',
    }

    def __init__(self):
        super().__init__()

        self.whitespace_re = regex.compile(b'[ \t\r\n]+', regex.ASCII)
        self.base64_re = regex.compile(b'^[-+_/A-Za-z0-9=]+$', regex.ASCII)

    def _apply(self, value):
        value = self._filter(value, Type(bytes))  # type: bytes

        if self._has_errors:
            return None

        # Strip out whitespace.
        # Technically, whitespace is not part of the Base64 alphabet, but
        # virtually every implementation allows it.
        value = self.whitespace_re.sub(b'', value)

        # Check for invalid characters.
        # Note that Python 3's b64decode does this for us, but we also have to
        # support Python 2.
        # https://docs.python.org/3/library/base64.html#base64.b64decode
        if not self.base64_re.match(value):
            return self._invalid_value(
                value=value,
                reason=self.CODE_INVALID,
            )

        # Check to see if we are working with a URL-safe dialect.
        # https://en.wikipedia.org/wiki/Base64#URL_applications
        if (b'_' in value) or (b'-' in value):
            # You can't mix dialects, silly!
            if (b'+' in value) or (b'/' in value):
                return self._invalid_value(
                    value=value,
                    reason=self.CODE_INVALID,
                )

            url_safe = True
        else:
            url_safe = False

        # Normalize padding.
        # http://stackoverflow.com/a/9807138/
        value = value.rstrip(b'=')
        value += (b'=' * (4 - (len(value) % 4)))

        try:
            return (
                urlsafe_b64decode(value)
                if url_safe
                else standard_b64decode(value)
            )
        except TypeError:
            return self._invalid_value(value, self.CODE_INVALID, exc_info=True)


class CaseFold(BaseFilter):
    """
    Applies case folding to an incoming string, allowing you to perform
    case-insensitive comparisons.

    The result tends to be lowercase, but it is recommended that you NOT treat
    CaseFold as a Unicode-aware lowercase filter!  The proper way to lowercase
    a string is very much locale-dependent.

    Note that the built-in :py:meth:`str.upper` and :py:meth:`str.lower`
    methods tend do a pretty good job of properly changing the case of unicode
    strings.

    References:
      - http://www.w3.org/International/wiki/Case_folding
      - https://docs.python.org/3/library/stdtypes.html#str.lower
      - https://docs.python.org/3/library/stdtypes.html#str.upper
    """

    def _apply(self, value):
        value = self._filter(value, Type(str))  # type: str

        if self._has_errors:
            return None

        return value.casefold()


class Choice(BaseFilter):
    """
    Requires an incoming value to match one of a set of allowed options.

    By default, the comparison is case-sensitive, but you can control this via
    the filter's initialiser.

    .. note::

       This filter is technically able to work with any hashable value, not
       just strings.
    """
    CODE_INVALID = 'not_valid_choice'

    templates = {
        CODE_INVALID: 'Valid options are: {choices}',
    }

    def __init__(self,
            choices: typing.Iterable[typing.Hashable],
            case_sensitive: bool = True,
    ) -> None:
        """
        :param choices:
            The allowed options; if an incoming value doesn't match any of
            these values, it is invalid.

        :param case_sensitive:
            Whether the comparison should be case-sensitive.
        """
        super().__init__()

        self.case_sensitive: bool = case_sensitive

        self.choice_map: typing.Dict[typing.Hashable, typing.Hashable] = {}

        for choice in choices:
            if self.case_sensitive or not isinstance(choice, typing.Text):
                self.choice_map[choice] = choice
            else:
                self.choice_map[CaseFold().apply(choice)] = choice

    def __str__(self):
        return '{type}({choices!r})'.format(
            type=type(self).__name__,
            choices=sorted(map(str, self.choice_map.values())),
        )

    def _apply(self, value):
        if (not self.case_sensitive) and isinstance(value, typing.Text):
            value = self._filter(value, CaseFold)

            if self._has_errors:
                return None

        try:
            return self.choice_map[value]
        except KeyError:
            return self._invalid_value(
                value=value,
                reason=self.CODE_INVALID,
                exc_info=True,

                template_vars={
                    'choices': sorted(map(str, self.choice_map.values())),
                },
            )


class IpAddress(BaseFilter):
    """
    Validates an incoming value as an IPv[46] address.
    """
    CODE_INVALID = 'not_ip_address'

    templates = {
        CODE_INVALID: 'This value is not a valid {ip_type} address.',
    }

    def __init__(self, ipv4: bool = True, ipv6: bool = False) -> None:
        super().__init__()

        self.ipv4 = ipv4
        self.ipv6 = ipv6

    def __str__(self):
        return '{type}(ipv4={ipv4!r}, ipv6={ipv6!r})'.format(
            type=type(self).__name__,
            ipv4=self.ipv4,
            ipv6=self.ipv6,
        )

    @property
    def ip_type(self) -> typing.Text:
        """
        Returns the IP address versions that this Filter accepts.
        """
        return '/'.join(filter(None, [
            'IPv4' if self.ipv4 else None,
            'IPv6' if self.ipv6 else None,
        ]))

    def _apply(self, value):
        value: typing.Text = self._filter(value, Type(typing.Text))

        if self._has_errors:
            return None

        # http://stackoverflow.com/a/4017219
        if self.ipv4:
            try:
                socket.inet_pton(socket.AF_INET, value)
            except socket.error:
                pass
            else:
                return value

        if self.ipv6:
            try:
                n = socket.inet_pton(socket.AF_INET6, value)
            except socket.error:
                pass
            else:
                # Convert the binary value back into a string representation,
                # so that the end result is normalized.
                # https://en.wikipedia.org/wiki/IPv6_address#Presentation
                return socket.inet_ntop(socket.AF_INET6, n)

        # If we get here, we failed the above checks (or the Filter is
        # configured not to allow anything through).
        return self._invalid_value(
            value=value,
            reason=self.CODE_INVALID,

            template_vars={
                'ip_type': self.ip_type
            },
        )


class JsonDecode(BaseFilter):
    """
    Interprets the value as JSON.
    """
    CODE_INVALID = 'not_json'

    templates = {
        CODE_INVALID: 'This value is not valid JSON.',
    }

    def __init__(self, decoder: typing.Callable = json.loads) -> None:
        super().__init__()

        self.decoder = decoder

    def _apply(self, value):
        value: typing.Text = self._filter(value, Type(typing.Text))

        if self._has_errors:
            return None

        try:
            return self.decoder(value)
        except ValueError:
            return self._invalid_value(value, self.CODE_INVALID, exc_info=True)


class MaxBytes(BaseFilter):
    """
    Ensures that an incoming string value is small enough to fit into a
    specified number of bytes when encoded.

    .. note::

        The resulting value is always byte string.
    """
    CODE_TOO_LONG = 'too_long'

    templates = {
        CODE_TOO_LONG:
            'Value is too long (must be < {max_bytes} '
            'bytes when encoded using {encoding}).',
    }

    def __init__(
            self,
            max_bytes: int,
            truncate: bool = False,
            prefix: typing.Text = '',
            suffix: typing.Text = '',
            encoding: typing.Text = 'utf-8',
    ) -> None:
        """
        :param max_bytes:
            Max number of bytes to allow.

        :param truncate:
            How to handle values that are too long:

            - ``truncate is True``:  Return truncated string.
            - ``truncate is False``:  Treat as invalid value.

        :param prefix:
            Prefix to apply to truncated values.

            The prefix will count towards the number of bytes, so even with a
            prefix the resulting string will not exceed ``max_bytes`` in
            length.

            Ignored when the incoming value is short enough, or when
            ``truncate is False``.

        :param suffix:
            Suffix to apply to truncated values.

            The suffix will count towards the number of bytes, so even with a
            suffix the resulting string will not exceed ``max_bytes`` in
            length.

            Ignored when the incoming value is short enough, or when
            ``truncate is False``.

        :param encoding:
            The character encoding to check against.

            Note: This filter is optimized for UTF-8.
        """
        super().__init__()

        self.encoding = encoding
        self.max_bytes = max_bytes
        self.prefix = prefix
        self.suffix = suffix
        self.truncate = truncate

    def __str__(self):
        return '{type}({max_bytes!r}, encoding={encoding!r})'.format(
            type=type(self).__name__,
            max_bytes=self.max_bytes,
            encoding=self.encoding,
        )

    def _apply(self, value):
        """
        :return:
            Returns bytes, truncated to the correct length.

            Note: Might be a bit shorter than the max length, to avoid
            orphaning a multibyte sequence.
        """
        value: typing.Text = self._filter(
            value=value,

            filter_chain=(
                    Type((bytes, str,)) |
                    Unicode(encoding=self.encoding)
            ),
        )

        if self._has_errors:
            return None

        bytes_value = value.encode(self.encoding)

        if self.truncate:
            # Truncated values are considered valid.
            return self.truncate_bytes(bytes_value)

        if len(bytes_value) > self.max_bytes:
            # Else, too-long values are invalid.
            return self._invalid_value(
                value=value,
                reason=self.CODE_TOO_LONG,
                context={
                    'encoding': self.encoding,
                    'max_bytes': self.max_bytes,
                    'truncate': self.truncate,
                },
            )

        return bytes_value

    def truncate_bytes(self, bytes_value: bytes) -> bytes:
        """
        Truncates a too-long bytes value to the specified number of bytes,
        using the filter's current configuration.

        :return:
            Returns bytes, truncated to the correct length.

            Note: Might be a bit shorter than ``self.max_bytes``, to avoid
            orphaning a multibyte sequence.
        """
        if len(bytes_value) <= self.max_bytes:
            return bytes_value

        # Note that ``self.encoding`` may indicate a codec that
        # uses a BOM, so we have to do a little extra work to make
        # sure we don't insert extra BOMs in the resulting value.
        bom = len(''.encode(self.encoding))

        # Prefix can be prepended right away.
        if self.prefix:
            bytes_value = (
                    bytes_value[0:bom] +
                    self.prefix.encode(self.encoding)[bom:] +
                    bytes_value[bom:]
            )

        # Suffix has to be tucked away for later (otherwise, the first thing
        # we'd truncate would be the suffix!).
        encoded_suffix = (
            self.suffix.encode(self.encoding)[bom:]
            if self.suffix
            else b''
        )

        # Ensure we leave enough space for the suffix.
        target_bytes = self.max_bytes - len(encoded_suffix)

        # Edge case where ``self.max_bytes`` is so tiny that we can't even fit
        # the entire prefix+suffix into the end result.
        if target_bytes < 1:
            return b''

        # Truncating the value is a bit tricky, as we have to be careful not to
        # leave an unterminated multibyte sequence.
        if self.encoding.lower() in {'utf-8', 'utf8'}:
            #
            # This code works a bit faster than the generic routine (see below)
            # because we only have to inspect up to 4 bytes from the end of the
            # encoded value instead of having to repeatedly decode the entire
            # string.
            #
            # But, it only works for UTF-8.
            #
            truncated = bytes_value[0:target_bytes]

            # Walk backwards through the string until we hit certain sequences.
            for i, o in enumerate(reversed(truncated), start=1):
                # If the final byte is not part of a multibyte sequence, then
                # we can stop right away; there is no need to remove anything.
                if (i < 2) and (o < 0b10000000):
                    break

                # If this byte is a leading byte (the first byte in a multibyte
                # sequence), determine how many bytes we need to strip off the
                # end of the string so that we can decode it back into a
                # unicode if needed.
                if o >= 0b11000000:
                    # Note:  Assuming max 4 bytes per sequence.
                    # Should be good enough until extraterrestrial languages
                    # are encountered.
                    seq_length = (
                        4 if o >= 0b11110000 else
                        3 if o >= 0b11100000 else
                        2
                    )

                    # Now that we know how many bytes are in the final
                    # sequence, check to see if it is complete, and discard it
                    # if it is incomplete.
                    if seq_length != i:
                        truncated = truncated[0:-i]

                    break

                # Else, we have a continuation byte.  Continue walking
                # backwards through the string.

            return truncated + encoded_suffix

        else:
            trim = 0
            while True:
                # Progressively chop bytes off the end of the string until we
                # have something that can be successfully decoded using the
                # specified encoding.
                truncated = bytes_value[0:target_bytes - trim]

                try:
                    truncated.decode(self.encoding)
                except UnicodeDecodeError:
                    trim += 1
                else:
                    return bytes(truncated) + encoded_suffix

                # We should never get here, but just in case, we need to ensure
                # the loop eventually terminates (Python won't error if
                # ``max_bytes - trim`` goes negative, since the slice operator
                # accepts negative values).
                if trim >= target_bytes:
                    raise ValueError(
                        'Unable to truncate {bytes_value!r} to {target_bytes} '
                        'bytes when encoded using {encoding}.'.format(
                            bytes_value=bytes_value,
                            target_bytes=target_bytes,
                            encoding=self.encoding,
                        ),
                    )


class Regex(BaseFilter):
    """
    Matches a regular expression in the value.

    IMPORTANT: This filter returns a LIST of all sequences in the input value
    that matched the regex!

    IMPORTANT: This Filter uses the ``regex`` library, which behaves slightly
    differently than Python's ``re`` library.

    If you've never used ``regex`` before, try it; you'll never want to go
    back!

    References:
      - https://pypi.python.org/pypi/regex
    """
    CODE_INVALID = 'malformed'

    templates = {
        CODE_INVALID:
            'Value does not match regular expression {pattern}.',
    }

    pattern_types = (
        typing.Pattern,
        regex.regex.Pattern,
    )

    def __init__(self,
            pattern: typing.Union[typing.Text, typing.Pattern],
    ) -> None:
        """
        :param pattern:
            String pattern, or pre-compiled regex.

            IMPORTANT:  If you specify your own compiled regex, be sure to add
            the ``UNICODE`` flag for Unicode support!
        """
        super().__init__()

        self.regex = (
            pattern
            if isinstance(pattern, self.pattern_types)
            else regex.compile(pattern, regex.UNICODE)
        )

    def __str__(self):
        return '{type}({pattern!r})'.format(
            type=type(self).__name__,
            pattern=self.regex.pattern,
        )

    def _apply(self, value):
        value: typing.Text = self._filter(value, Type(typing.Text))

        if self._has_errors:
            return None

        matches = [
            match.group(0)
            for match in self.regex.finditer(value)
        ]

        if not matches:
            return self._invalid_value(
                value=value,
                reason=self.CODE_INVALID,

                template_vars={
                    'pattern': self.regex.pattern,
                },
            )

        return matches


class Split(BaseFilter):
    """
    Splits an incoming string into parts.

    The result is either a list or a dict, depending on whether you
    specify keys to map to the result.
    """

    # noinspection PyProtectedMember
    def __init__(
            self,
            pattern: typing.Union[typing.Text, typing.Pattern],
            keys: typing.Optional[typing.Sequence[typing.Text]] = None,
    ) -> None:
        """
        :param pattern:
            Regex used to split incoming string values.

            IMPORTANT:  If you specify your own compiled regex, be sure to add
            the ``UNICODE`` flag for Unicode support!

        :param keys:
            If set, the resulting list will be converted into a dict, using the
            specified keys.

            .. important::

               If ``keys`` is set, the split value's length must be less than
               or equal to ``len(keys)``.
        """
        super().__init__()

        self.regex = (
            pattern
            if isinstance(pattern, Regex.pattern_types)
            else regex.compile(pattern, regex.UNICODE)
        )

        self.keys = keys

    def __str__(self):
        return '{type}({pattern!r}, keys={keys!r}'.format(
            type=type(self).__name__,
            pattern=self.regex.pattern,
            keys=self.keys,
        )

    def _apply(self, value):
        value: typing.Text = self._filter(value, Type(typing.Text))

        if self._has_errors:
            return None

        split = self.regex.split(value)

        if self.keys:
            # The split value can have at most as many items as ``self.keys``.
            split = self._filter(split, MaxLength(len(self.keys)))

            if self._has_errors:
                return None

            return dict(zip_longest(self.keys, split))
        else:
            return split


class Strip(BaseFilter):
    """
    Strips characters (whitespace and non-printables by default) from the
    end(s) of a string.

    IMPORTANT:  This Filter uses the ``regex`` library, which behaves slightly
    differently than Python's ``re`` library.

    If you've never used ``regex`` before, try it; you'll never want to go
    back!
    """

    def __init__(
            self,
            leading: typing.Text = r'[\p{C}\s]+',
            trailing: typing.Text = r'[\p{C}\s]+',
    ) -> None:
        """
        :param leading:
            Regex to match at the start of the string.

        :param trailing:
            Regex to match at the end of the string.
        """
        super().__init__()

        if leading:
            self.leading = regex.compile(
                r'^{pattern}'.format(pattern=leading),
                regex.UNICODE,
            )
        else:
            self.leading = None

        if trailing:
            self.trailing = regex.compile(
                r'{pattern}$'.format(pattern=trailing),
                regex.UNICODE,
            )
        else:
            self.trailing = None

    def __str__(self):
        return '{type}(leading={leading!r}, trailing={trailing!r})'.format(
            type=type(self).__name__,
            leading=self.leading.pattern,
            trailing=self.trailing.pattern,
        )

    def _apply(self, value):
        value: typing.Text = self._filter(value, Type(typing.Text))

        if self._has_errors:
            return None

        if self.leading:
            value = self.leading.sub('', value)

        if self.trailing:
            value = self.trailing.sub('', value)

        return value


class Unicode(BaseFilter):
    """
    Converts a value into a unicode string.

    Note:  By default, additional normalization is applied to the resulting
    value.  See the initialiser docstring for more info.

    References:
      - https://docs.python.org/2/howto/unicode.html
      - https://en.wikipedia.org/wiki/Unicode_equivalence
    """
    CODE_DECODE_ERROR = 'wrong_encoding'

    templates = {
        CODE_DECODE_ERROR: 'This value cannot be decoded using {encoding}.',
    }

    def __init__(
            self,
            encoding: typing.Text = 'utf-8',
            normalize: bool = True,
    ) -> None:
        """
        :param encoding:
            Used to decode non-unicode values.

        :param normalize:
            Whether to normalize the resulting value:
                - Convert to NFC form.
                - Remove non-printable characters.
                - Convert all line endings to unix-style ('\n').
        """
        super().__init__()

        self.encoding = encoding
        self.normalize = normalize

        if self.normalize:
            #
            # Compile the regex that we will use to remove non- printables from
            # the resulting unicode.
            # http://www.regular-expressions.info/unicode.html#category
            #
            # Note: using a double negative so that we can exclude newlines,
            # which are technically considered control chars.
            # http://stackoverflow.com/a/3469155
            #
            self.npr = regex.compile(r'[^\P{C}\s]+', regex.UNICODE)

    def __str__(self):
        return '{type}(encoding={encoding!r})'.format(
            type=type(self).__name__,
            encoding=self.encoding,
        )

    def _apply(self, value):
        try:
            if isinstance(value, typing.Text):
                decoded = value

            elif isinstance(value, bytes):
                decoded = value.decode(self.encoding)

            elif isinstance(value, bool):
                decoded = str(int(value))

            # In Python 3, ``bytes(<int>)`` does weird things.
            # https://www.python.org/dev/peps/pep-0467/
            elif isinstance(value, (int, float)):
                decoded = str(value)

            elif isinstance(value, DecimalType):
                decoded = format(value, 'f')

            elif isinstance(value, Element):
                # There's no way (that I know of) to get
                # :py:meth:`ElementTree.tostring` to return a str.
                decoded = tostring(value, 'utf-8').decode('utf-8')

            elif hasattr(value, '__bytes__'):
                decoded = bytes(value).decode(self.encoding)

            else:
                decoded = str(value)
        except UnicodeDecodeError:
            return self._invalid_value(
                value=value,
                reason=self.CODE_DECODE_ERROR,
                exc_info=True,

                template_vars={
                    'encoding': self.encoding,
                },
            )

        if self.normalize:
            return (
                # Return the final string in composed form.
                # https://en.wikipedia.org/wiki/Unicode_equivalence
                unicodedata.normalize('NFC',
                    # Remove non-printables.
                    self.npr.sub('', decoded)
                )
                # Normalize line endings.
                # http://stackoverflow.com/a/1749887
                .replace('\r\n', '\n')
                .replace('\r', '\n')
            )
        else:
            return decoded


class ByteString(Unicode):
    """
    Converts a value into a byte string, encoded as UTF-8.

    IMPORTANT: This filter returns bytes objects, not bytearrays!
    """

    def __init__(
            self,
            encoding: typing.Text = 'utf-8',
            normalize: bool = False,
    ) -> None:
        """
        :param encoding:
            Used to decode non-unicode values.

        :param normalize:
            Whether to normalize the unicode value before converting
            back into bytes:

                - Convert to NFC form.
                - Remove non-printable characters.
                - Convert all line endings to unix-style ('\n').

            Note that ``normalize`` is ``False`` by default for
            :py:class:`ByteString`, but ``True`` by default for
            :py:class:`Unicode`.
        """
        super().__init__(encoding, normalize)

    # noinspection SpellCheckingInspection
    def _apply(self, value):
        decoded: typing.Text = super()._apply(value)

        #
        # No need to catch UnicodeEncodeErrors here; UTF-8 can handle any
        # unicode value.
        #
        # Technically, we could get this error if we encounter a code point
        # beyond U+10FFFF (the highest valid code point in the Unicode
        # standard).
        #
        # However, it's not possible to create a `unicode` object with an
        # invalid code point, so we wouldn't even be able to get this far if
        # the incoming value contained a character that can't be represented
        # using UTF-8.
        #
        # Note that in some (very old and no-longer-supported) versions of
        # Python, it is possible (albeit really difficult) to trick Python into
        # creating unicode objects with invalid code points, but it generally
        # requires using specific codecs that aren't UTF-8.
        #
        # Example of exploit and release notes from the Python release (2.7.6)
        # that fixes the issue:
        #
        #   - https://gist.github.com/rspeer/7559750
        #   - https://hg.python.org/cpython/raw-file/99d03261c1ba/Misc/NEWS
        #

        # Normally we return ``None`` if we get any errors, but in this case,
        # we'll let the superclass method decide.
        return decoded if self._has_errors else decoded.encode('utf-8')


class Uuid(BaseFilter):
    """
    Interprets an incoming value as a UUID.
    """
    CODE_INVALID = 'not_uuid'
    CODE_WRONG_VERSION = 'wrong_version'

    templates = {
        CODE_INVALID: 'This value is not a well-formed UUID.',

        CODE_WRONG_VERSION:
            'v{incoming} UUID not allowed (expected v{expected}).',
    }

    def __init__(self, version: typing.Optional[int] = None) -> None:
        """
        :type version:
            If specified, requires the resulting UUID to match the specified
            version.

        References:
          - https://en.wikipedia.org/wiki/Uuid#RFC_4122_Variant
        """
        super().__init__()

        self.version = version

    def __str__(self):
        return '{type}(version={version!r})'.format(
            type=type(self).__name__,
            version=self.version,
        )

    def _apply(self, value):
        value: typing.Union[typing.Text, UUID] = self._filter(
            value,
            Type((typing.Text, UUID)),
        )

        if self._has_errors:
            return None

        try:
            uuid = (
                value
                if isinstance(value, UUID)
                else UUID(hex=value)
            )
        except ValueError:
            return self._invalid_value(value, self.CODE_INVALID, exc_info=True)
        else:
            if self.version not in (None, uuid.version):
                return self._invalid_value(
                    value=str(uuid),
                    reason=self.CODE_WRONG_VERSION,

                    context={
                        'expected': self.version,
                        'incoming': uuid.version,
                    },
                )

            return uuid
