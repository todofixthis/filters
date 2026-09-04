from abc import ABCMeta
from collections.abc import Callable
from functools import WRAPPER_ASSIGNMENTS, partial
from typing import Any

from filters.base import BaseFilter, FilterCompatible, FilterMeta

__all__ = [
    "FilterMacroType",
    "filter_macro",
]


class FilterMacroType(BaseFilter, metaclass=ABCMeta):
    """Base type for filter macros.

    Doesn't do anything on its own, but it is useful for identifying
    filter macros when paired with an ``issubclass`` check.

    Important: Use ``issubclass``, not ``isinstance``!

    Example::

       @filter_macro
       def MyMacro():
         return f.NoOp

       # ``MyMacro`` is now a *subclass* of ``FilterMacroType``!
       assert issubclass(MyMacro, FilterMacroType)

       # It is *not* an *instance* of ``FilterMacroType``!
       assert not isinstance(MyMacro, FilterMacroType)
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Never actually runs: ``FilterMacroMeta.__call__`` intercepts
        # instantiation and hands runtime args straight to the wrapped
        # function instead. This override exists only so that static
        # type checkers accept calls like ``SomeMacro(some_kwarg=...)``
        # against the macro's erased ``type[FilterMacroType]`` return
        # type -- there's no way to thread the wrapped function's real
        # signature through ``filter_macro``'s return type.
        super().__init__()


def filter_macro(
    func: Callable[..., FilterCompatible],
    *args: Any,
    **kwargs: Any,
) -> type[FilterMacroType]:
    """Promotes a function returning a filter into its own filter type.

    Example::

        @filter_macro
        def String():
            return Unicode | Strip | NotEmpty

        # You can now use `String` anywhere you would use a regular
        # Filter:
        (String | Split(':')).apply('...')

    You can also use ``filter_macro`` to create partials, allowing you
    to preset one or more initialisation arguments::

        Minor = filter_macro(Max, max_value=18, inclusive=False)
        Minor(inclusive=True).apply(18)

    Args:
        func: The function to promote to a filter type.
        *args: Positional arguments to preset.
        **kwargs: Keyword arguments to preset.

    Returns:
        A new filter type based on the function.
    """
    filter_partial = partial(func, *args, **kwargs)

    class FilterMacroMeta(FilterMeta):
        @staticmethod
        def __new__(mcs, name, bases, attrs):
            # This is as close as we can get to running
            # ``update_wrapper`` on a type.
            for attr in WRAPPER_ASSIGNMENTS:
                if hasattr(func, attr):
                    attrs[attr] = getattr(func, attr)

            # Note that we ignore the ``name`` argument, passing in
            # ``func.__name__`` instead.
            return super().__new__(mcs, func.__name__, bases, attrs)

        def __call__(cls, *runtime_args, **runtime_kwargs):
            return filter_partial(*runtime_args, **runtime_kwargs)

    class FilterMacro(FilterMacroType, metaclass=FilterMacroMeta):
        # This method will probably never get called due to overloaded
        # ``__call__`` in the metaclass, but just in case, we'll include
        # it because it is an abstract method in `BaseFilter`.
        def _apply(self, value):
            # noinspection PyProtectedMember
            return self.__class__()._apply(value)

    return FilterMacro
