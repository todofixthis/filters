import typing

import filters as f


class FilterAlpha(f.BaseFilter):
    """
    A filter that can be used for testing.
    """

    def _apply(self, value: typing.Any) -> typing.Any:
        return value


class FilterBravo(f.BaseFilter):
    """
    A filter that will can be used for testing.
    """

    def __init__(self, name: typing.Optional[str] = None) -> None:
        super().__init__()

        self.name = name

    def _apply(self, value: typing.Any) -> typing.Any:
        return value


@f.filter_macro
def FilterCharlie() -> type[f.NoOp]:
    """
    A filter macro that can be used for testing.
    """
    return f.NoOp
