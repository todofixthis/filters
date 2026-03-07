from decimal import Decimal as DecimalType, InvalidOperation, ROUND_HALF_UP
from typing import Any

from filters.base import BaseFilter, Type

__all__ = [
    "Decimal",
    "Int",
    "Max",
    "Min",
    "Round",
]


class Decimal(BaseFilter):
    """Interprets the value as a :py:class:`decimal.Decimal` object."""

    CODE_INVALID = "not_numeric"
    CODE_NON_FINITE = "not_finite"

    templates = {
        CODE_INVALID: "Numeric value expected.",
        CODE_NON_FINITE: "Numeric value expected.",
    }

    def __init__(
        self,
        max_precision: int | DecimalType | None = None,
        allow_tuples: bool = True,
    ) -> None:
        """Initialises the Decimal filter.

        Args:
            max_precision: Max number of decimal places the resulting
                value is allowed to have. Values that are too precise
                will be rounded to fit.

                To avoid ambiguity, specify ``max_precision`` as a
                ``decimal.Decimal`` object.

                For example, to round to the nearest 1/100::

                    Decimal(max_precision=decimal.Decimal('0.01'))
            allow_tuples: Whether to allow tuple-like inputs.

                Allowing tuple inputs might couple the implementation
                more tightly to Python's Decimal type, so you have the
                option to disallow it.
        """
        super().__init__()

        # Convert e.g., 3 => DecimalType('.001').
        if not ((max_precision is None) or isinstance(max_precision, DecimalType)):
            max_precision = DecimalType(".1") ** max_precision

        self.max_precision = max_precision
        self.allow_tuples = allow_tuples

    def __str__(self):
        return f"{type(self).__name__}(max_precision={self.max_precision!r})"

    def _apply(self, value):
        allowed_types = (
            str,
            int,
            float,
            DecimalType,
        )
        if self.allow_tuples:
            # Python's Decimal type supports both tuples and lists.
            # :py:meth:`decimal.Decimal.__init__`
            allowed_types += (
                list,
                tuple,
            )

        value = self._filter(value, Type(allowed_types))

        if self._has_errors:
            return value

        try:
            d = DecimalType(value)
        except (InvalidOperation, TypeError, ValueError):
            return self._invalid_value(value, self.CODE_INVALID, exc_info=True)

        # Decimal's constructor also accepts values such as 'NaN' or
        # '+Inf', which aren't valid in this context.
        # :see: decimal.Decimal._parser
        if not d.is_finite():
            return self._invalid_value(
                value=value,
                reason=self.CODE_NON_FINITE,
                exc_info=True,
            )

        if self.max_precision is not None:
            d = d.quantize(self.max_precision)

        return d


class Int(BaseFilter):
    """Interprets the value as an int.

    Strings and other compatible values will be converted, but floats
    will be treated as INVALID.

    Note:
        Python handles really, really big int values transparently, so
        you don't need to worry about overflow.

        Reference: http://stackoverflow.com/a/538583
    """

    CODE_DECIMAL = "not_int"

    templates = {
        CODE_DECIMAL: "Integer value expected.",
    }

    def _apply(self, value):
        decimal: DecimalType = self._filter(value, Decimal)

        if self._has_errors:
            return None

        # Do not allow floats.
        # http://stackoverflow.com/a/19965088
        if decimal % 1:
            return self._invalid_value(value, self.CODE_DECIMAL)

        # Once we get to this point, we're pretty confident that we've
        # got something that can be converted into an int.
        # noinspection PyTypeChecker
        return int(decimal)


class Max(BaseFilter):
    """Enforces a maximum value.

    Note:
        Technically, this filter can operate on any type that supports
        comparison, but it tends to be used exclusively with numeric
        types.
    """

    CODE_TOO_BIG = "too_big"

    templates = {
        CODE_TOO_BIG: "Value is too large (must be {operator} {max}).",
    }

    def __init__(self, max_value: Any, exclusive: bool = False) -> None:
        """Initialises the Max filter.

        Args:
            max_value: The max value that the Filter will accept.
            exclusive: Whether to exclude the max value itself as a
                valid value:

                - True: The incoming value must be *less than* the max
                  value.
                - False (default): The incoming value must be *less than
                  or equal to* the max value.
        """
        super().__init__()

        self.max_value = max_value
        self.exclusive = exclusive

    def __str__(self):
        return (
            f"{type(self).__name__}({self.max_value!r}, exclusive={self.exclusive!r})"
        )

    def _apply(self, value):
        # Note that this will yield weird results for string values.
        # We could add better unicode support, if we ever need it.
        # http://stackoverflow.com/q/1097908
        if (value > self.max_value) or (self.exclusive and (value == self.max_value)):
            return self._invalid_value(
                value=value,
                reason=self.CODE_TOO_BIG,
                # This only makes sense if `self.exclusive` is False.
                # Better to be consistent and replace all invalid
                # values with `None`.
                # replacement = self.max_value,
                template_vars={
                    "operator": "<" if self.exclusive else "<=",
                    "max": self.max_value,
                },
            )

        return value


class Min(BaseFilter):
    """Enforces a minimum value.

    Note:
        Technically, this filter can operate on any type that supports
        comparison, but it tends to be used exclusively with numeric
        types.
    """

    CODE_TOO_SMALL = "too_small"

    templates = {
        CODE_TOO_SMALL: "Value is too small (must be {operator} {min}).",
    }

    def __init__(self, min_value: Any, exclusive: bool = False) -> None:
        """Initialises the Min filter.

        Args:
            min_value: The min value that the Filter will accept.
            exclusive: Whether to exclude the min value itself as a
                valid value:

                - True: The incoming value must be *greater than* the
                  min value.
                - False (default): The incoming value must be *greater
                  than or equal to* the min value.
        """
        super().__init__()

        self.min_value = min_value
        self.exclusive = exclusive

    def __str__(self):
        return (
            f"{type(self).__name__}({self.min_value!r}, exclusive={self.exclusive!r})"
        )

    def _apply(self, value):
        # Note that this will yield weird results for string values.
        # We could add better unicode support, if we ever need it.
        # http://stackoverflow.com/q/1097908
        if (value < self.min_value) or (self.exclusive and (value == self.min_value)):
            return self._invalid_value(
                value=value,
                reason=self.CODE_TOO_SMALL,
                # This only makes sense if ``self.exclusive`` is False.
                # Better to be consistent and replace all invalid
                # values with ``None``.
                # replacement = self.min_value,
                template_vars={
                    "operator": ">" if self.exclusive else ">=",
                    "min": self.min_value,
                },
            )

        return value


class Round(BaseFilter):
    """Rounds incoming values to whole numbers or decimals."""

    def __init__(
        self,
        to_nearest: int | str | DecimalType = 1,
        rounding: str = ROUND_HALF_UP,
        result_type: type = DecimalType,
    ):
        """Initialises the Round filter.

        Args:
            to_nearest: The value that the filter should round to.

                E.g., ``Round(1)`` rounds to the nearest whole number.

                If you want to round to a float value, it is recommended
                that you provide it as a string or Decimal, to avoid
                floating point precision errors.
            rounding: Controls how to round values.
            result_type: The type of result to return.
        """
        super().__init__()

        self.to_nearest = DecimalType(to_nearest)

        # Rounding to negative values isn't supported.
        # I'm not even sure if that concept is valid.
        Min(DecimalType("0")).apply(self.to_nearest)

        self.result_type = result_type
        self.rounding = rounding

    def _apply(self, value):
        value: DecimalType = self._filter(value, Decimal)

        if self._has_errors:
            return None

        one = DecimalType("1")

        # Scale, round, unscale.
        # Note that we use :py:meth:`decimal.Decimal.quantize` instead of
        # :py:func:`round` to avoid floating-point precision errors.
        # http://stackoverflow.com/a/4340355
        return self.result_type(
            (value * one / self.to_nearest).quantize(one, rounding=self.rounding)
            * self.to_nearest
        )
