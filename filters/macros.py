from abc import ABCMeta
from functools import WRAPPER_ASSIGNMENTS, partial

from filters.base import BaseFilter, FilterMeta

__all__ = [
    'FilterMacroType',
    'filter_macro',
]


class FilterMacroType(BaseFilter, metaclass=ABCMeta):
    """
    Base type for filter macros.  Doesn't do anything on its own, but
    it is useful for identifying filter macros when paired with an
    ``issubclass`` check.

    Important:  Use ``issubclass``, not ``isinstance``!

    .. code-block:: python

       @filter_macro
       def MyMacro():
         return f.NoOp

       # ``MyMacro`` is now a *subclass* of ``FilterMacroType``!
       assert issubclass(MyMacro, FilterMacroType)

       # It is *not* an *instance* of ``FilterMacroType``!
       assert not isinstance(MyMacro, FilterMacroType)
    """
    pass


def filter_macro(func, *args, **kwargs):
    """
    Promotes a function that returns a filter into its own filter type.

    Example::

        @filter_macro
        def String():
            return Unicode | Strip | NotEmpty

        # You can now use `String` anywhere you would use a regular Filter:
        (String | Split(':')).apply('...')

    You can also use ``filter_macro`` to create partials, allowing you to
    preset one or more initialization arguments::

        Minor = filter_macro(Max, max_value=18, inclusive=False)
        Minor(inclusive=True).apply(18)
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
            return super() \
                .__new__(mcs, func.__name__, bases, attrs)

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
