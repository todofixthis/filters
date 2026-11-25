"""
Internal test helpers for the phx-filters test suite.

Fixtures (``assert_filter_passes``, ``assert_filter_errors``) and sentinels
(``unmodified``, ``skip_value_check``) are provided by the ``filters``
pytest plugin — no import needed.

For ``assert_filter_passes``: when a filter passes a value through unchanged,
the third argument (``expected``) can be omitted — the fixture uses the input
``value`` as the expected output.
"""

import typing
from typing import Any


class Bytesy:
    """
    A class that defines ``__bytes__``, used to test filters that convert
    values into byte strings.
    """

    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value

    def __bytes__(self) -> bytes:
        return bytes(self.value)


class Lengthy(typing.Sized):
    """
    A class that defines ``__len__``, used to test filters that check for
    object length.
    """

    def __init__(self, length: int) -> None:
        super().__init__()
        self.length = length

    def __len__(self) -> int:
        return self.length


class Unicody:
    """
    A class that defines ``__str__``, used to test filters that convert values
    into unicodes.
    """

    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value

    def __str__(self) -> str:
        return str(self.value)
