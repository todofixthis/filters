import typing
import warnings
from abc import abstractmethod as abstract_method
from decimal import Decimal as DecimalType, InvalidOperation, ROUND_HALF_UP

from filters.base import BaseFilter, InvalidValue, Type

__all__ = [
    "Decimal",
    "Int",
    "Max",
    "Min",
    "Round",
]

T = typing.TypeVar("T")


class _Comparable(typing.Protocol):
    """
    Used to validate that the value passed to a filter supports comparison methods.

    :see: https://stackoverflow.com/a/65224102
    """

    @abstract_method
    def __lt__(self: typing.Any, other: typing.Any, /) -> bool:
        pass


class Decimal(BaseFilter[DecimalType]):
    """
    Interprets the value as a :py:class:`decimal.Decimal` object.
    """

    CODE_INVALID = "not_numeric"
    CODE_NON_FINITE = "not_finite"

    templates = {
        CODE_INVALID: "Numeric value expected.",
        CODE_NON_FINITE: "Finite value expected.",
    }

    def __init__(
        self,
        max_precision: int | DecimalType | None = None,
        allow_tuples: bool = True,
    ) -> None:
        """
        :param max_precision:
            Max number of decimal places the resulting value is allowed to have. Values
            that are too precise will be rounded to fit.

            To avoid ambiguity, specify ``max_precision`` as a ``decimal.Decimal``
            object.

            For example, to round to the nearest 1/100::

                Decimal(max_precision=decimal.Decimal('0.01'))

        :param allow_tuples:
            Whether to allow tuple-like inputs.

            Allowing tuple inputs might couple the implementation more tightly to
            Python's Decimal type, so you can choose to disallow it.
        """
        super().__init__()

        # Convert e.g., 3 => DecimalType('.001').
        if not ((max_precision is None) or isinstance(max_precision, DecimalType)):
            max_precision = DecimalType(".1") ** max_precision

        self.max_precision = max_precision
        self.allow_tuples = allow_tuples

    def __str__(self) -> str:
        return "{type}(max_precision={max_precision!r})".format(
            type=type(self).__name__,
            max_precision=self.max_precision,
        )

    def _apply(self, value: typing.Any) -> DecimalType:
        # Python's Decimal type supports both tuples and lists.
        # :py:meth:`decimal.Decimal.__init__`
        allowed_types = (
            (str, int, float, DecimalType, list, tuple)
            if self.allow_tuples
            else (
                str,
                int,
                float,
                DecimalType,
            )
        )

        value = self._filter(value, Type(allowed_types))

        try:
            d = DecimalType(value)
        except (InvalidOperation, TypeError, ValueError) as e:
            raise InvalidValue(self, value, self.CODE_INVALID) from e

        # Decimal's constructor also accepts values such as 'NaN' or '+Inf', which
        # aren't valid in this context.
        # :see: decimal.Decimal._parser
        if not d.is_finite():
            raise InvalidValue(self, value, self.CODE_NON_FINITE)

        if self.max_precision is not None:
            d = d.quantize(self.max_precision)

        return d


class Int(BaseFilter[int]):
    """
    Interprets the value as an int.

    Strings and other compatible values will be converted.

    Floats will be accepted as long as the fpart is empty (e.g. 42.0 is valid, but 42.1
    is not).

    If you want to accept float values with non-empty fparts, pass the value through
    :py:class:`Round` first.

    Note that `Python handles massive int values transparently`_, so you don't need to
    worry about overflow.


    .. _Python handles massive int values transparently: http://stackoverflow.com/a/538583
    """

    CODE_DECIMAL = "not_int"

    templates = {
        CODE_DECIMAL: "Integer value expected.",
    }

    def _apply(self, value: typing.Any) -> int:
        decimal_value: DecimalType = self._filter(value, Decimal())

        # Do not allow floats.
        # http://stackoverflow.com/a/19965088
        if decimal_value % 1:
            raise InvalidValue(self, value, self.CODE_DECIMAL)

        # Once we get to this point, we're pretty confident we've got something that can
        # be converted into an int.
        return int(decimal_value)


class Max[T: _Comparable](BaseFilter[T]):
    """
    Enforces a maximum value.

    .. note:
        Technically, this filter can operate on any type that supports comparison, but
        it tends to be used exclusively with numeric types.

        In particular, it tends to yield `strange results when applied to strings`_.

        .. _`strange results when applied to strings`: http://stackoverflow.com/q/1097908
    """

    CODE_TOO_BIG = "too_big"

    templates = {
        CODE_TOO_BIG: "Value is too large (must be {operator} {max}).",
    }

    def __init__(self, max_value: T, exclusive: bool = False) -> None:
        """
        :param max_value:
            The max value that the Filter will accept.

        :param exclusive:
            Whether to exclude the max value itself as a valid value:

            - True: The incoming value must be *less than* the max value.
            - False (default): The incoming value must be *less than or equal
              to* the max value.
        """
        super().__init__()

        self.max_value = max_value
        self.exclusive = exclusive

    def __str__(self) -> str:
        return "{type}({max_value!r}, exclusive={exclusive!r})".format(
            type=type(self).__name__,
            max_value=self.max_value,
            exclusive=self.exclusive,
        )

    def _apply[U: _Comparable](self, value: U) -> U:
        if (value > self.max_value) or (self.exclusive and (value == self.max_value)):
            raise InvalidValue(
                self,
                value,
                self.CODE_TOO_BIG,
                template_vars={
                    "operator": "<" if self.exclusive else "<=",
                    "max": str(self.max_value),
                },
            )

        return value


class Min[T: _Comparable](BaseFilter[T]):
    """
    Enforces a minimum value.

    .. note:
        Technically, this filter can operate on any type that supports comparison, but
        it tends to be used exclusively with numeric types.

        In particular, it tends to yield `strange results when applied to strings`_.

        .. _`strange results when applied to strings`: http://stackoverflow.com/q/1097908
    """

    CODE_TOO_SMALL = "too_small"

    templates = {
        CODE_TOO_SMALL: "Value is too small (must be {operator} {min}).",
    }

    def __init__(self, min_value: T, exclusive: bool = False) -> None:
        """
        :param min_value:
            The min value that the Filter will accept.

        :param exclusive:
            Whether to exclude the min value itself as a valid value:

            - True: The incoming value must be *greater than* the min
              value.
            - False (default): The incoming value must be *greater than
              or equal to* the min value.
        """
        super().__init__()

        self.min_value = min_value
        self.exclusive = exclusive

    def __str__(self) -> str:
        return "{type}({min_value!r}, exclusive={exclusive!r})".format(
            type=type(self).__name__,
            min_value=self.min_value,
            exclusive=self.exclusive,
        )

    def _apply[U: _Comparable](self, value: U) -> U:
        if (value < self.min_value) or (self.exclusive and (value == self.min_value)):
            raise InvalidValue(
                self,
                value,
                self.CODE_TOO_SMALL,
                template_vars={
                    "operator": ">" if self.exclusive else ">=",
                    "min": str(self.min_value),
                },
            )

        return value


class Round(BaseFilter[DecimalType]):
    """
    Rounds incoming values to whole numbers or decimals.
    """

    def __init__(
        self,
        to_nearest: int | str | DecimalType = 1,
        rounding: str = ROUND_HALF_UP,
    ):
        """
        :param to_nearest:
            The value that the filter should round to.

            E.g. ``Round(1)`` rounds to the nearest whole number.

            If you want to round to a float value, it is recommended that you provide it
            as a string or Decimal, to avoid floating point precision errors.

        :param rounding:
            Controls how to round values.

            See https://docs.python.org/3/library/decimal.html#rounding-modes for
            available rounding modes.
        """
        super().__init__()

        if isinstance(to_nearest, float):
            warnings.warn(
                "Specifying `to_nearest` as a float may cause floating point issues. "
                "For safety, always specify `to_nearest` as a string."
            )

        self.to_nearest = DecimalType(to_nearest)

        # Rounding to zero / negative values isn't supported.
        # I'm not even sure if that concept is valid.
        self._filter(self.to_nearest, Min(DecimalType("0"), exclusive=True))

        self.mode = rounding

    def _apply(self, value: typing.Any) -> DecimalType:
        value = self._filter(value, Decimal())

        one = DecimalType("1")

        # Scale -> round -> unscale.
        # Note that we use :py:meth:`decimal.Decimal.quantize` instead of
        # :py:func:`round` to avoid floating-point precision errors.
        # :see: http://stackoverflow.com/a/4340355
        return DecimalType(
            (value * one / self.to_nearest).quantize(one, rounding=self.mode)
            * self.to_nearest
        )
