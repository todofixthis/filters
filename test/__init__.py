import typing

from filters.base import BaseFilter


class FilterAlpha(BaseFilter):
    """
    A filter that can be used for testing.
    """

    def _apply(self, value):
        return value


class FilterBravo(BaseFilter):
    """
    A filter that will can be used for testing.
    """

    def __init__(self, name: typing.Optional[str] = None) -> None:
        super().__init__()

        self.name = name

    def _apply(self, value):
        return value
