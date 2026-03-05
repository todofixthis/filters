from collections.abc import Generator
from importlib.metadata import entry_points
from inspect import (
    getmembers as get_members,
    isabstract as is_abstract,
    isclass as is_class,
    ismodule as is_module,
)
from logging import getLogger
from typing import Any, Hashable

from class_registry.entry_points import EntryPointClassRegistry

from filters.base import BaseFilter

__all__ = [
    "FilterExtensionRegistry",
    "GROUP_NAME",
]

GROUP_NAME = "filters.extensions"
"""The key to use when declaring entry points in ``pyproject.toml``.

Example::

   [project.entry-points."filters.extensions"]
   Country = "filters_iso:Country"
   Currency = "filters_iso:Currency"

Filters that are loaded this way are accessible from
:py:data:`filters.ext` (not imported into the global namespace
because it gives IDEs a heart attack).
"""

logger = getLogger(__name__)


class FilterExtensionRegistry(EntryPointClassRegistry[BaseFilter]):
    """Creates a registry that can be used to dynamically load 3rd-party
    filters into the (nearly) top-level namespace.
    """

    def __init__(self, group: str = GROUP_NAME) -> None:
        """Initialises the FilterExtensionRegistry.

        Args:
            group: The entry point group name to use. Defaults to
                GROUP_NAME.
        """
        super().__init__(group)

    def __getattr__(self, item: str) -> type[BaseFilter]:
        """Provides attr-like interface for accessing extension filters.

        The default interface for class registries is to access items
        rather than attributes.

        Args:
            item: The name of the filter to access.

        Returns:
            The filter class.
        """
        # create_instance returns the class itself (not an instance) when called
        # without args, so the runtime type is type[BaseFilter], not BaseFilter.
        return self[item]  # type: ignore[return-value]

    def __repr__(self):
        return repr(self._get_cache())

    def _get_cache(self) -> dict[Hashable, type[BaseFilter]]:
        if self._cache is None:
            self._cache = {}

            for target in entry_points(group=self.group):
                filter_ = target.load()

                ift_result = is_filter_type(filter_)

                if ift_result is True:
                    logger.debug(
                        f"Registering extension filter "
                        f"{filter_.__module__}.{filter_.__name__} as {target.name}.",
                    )

                    self._cache[target.name] = filter_

        return self._cache

    @staticmethod
    def create_instance(class_: type, *args, **kwargs) -> Any:
        """Returns the class itself when called with no arguments.

        Overrides the default behaviour (which would instantiate the class)
        so that extension filters behave consistently with
        :py:meth:`filters.base.FilterMeta.__or__`, which chains uninstantiated
        filter classes directly (e.g. ``filters.ext.MyFilter | OtherFilter``).

        Args:
            class_: The filter class to return or instantiate.
            *args: Positional arguments forwarded to the class constructor.
            **kwargs: Keyword arguments forwarded to the class constructor.

        Returns:
            The class itself if no arguments are provided; otherwise a new
            instance of the class.
        """
        if args or kwargs:
            return class_(*args, **kwargs)

        return class_


def is_filter_type(target: Any) -> bool | str:
    """Returns whether the specified object can be registered as a filter.

    Args:
        target: The object to check.

    Returns:
        Returns ``True`` if the object is a filter. Otherwise, returns
        a string indicating why it is not valid.
    """
    if not is_class(target):
        return "not a class"

    if not issubclass(target, BaseFilter):
        return "does not extend BaseFilter"

    if is_abstract(target):
        return "abstract class"

    return True


def iter_filters_in(
    target: Any,
) -> Generator[tuple[str, type[BaseFilter]], None, None]:
    """Iterates over all filters in the specified module/class.

    Args:
        target: The module or class to iterate over.

    Yields:
        Tuples of (filter_name, filter_class) for each filter found.
    """
    ift_result = is_filter_type(target)

    if ift_result is True:
        logger.debug(
            f"Registering extension filter " f"{target.__module__}.{target.__name__}.",
        )

        yield target.__name__, target
    elif is_module(target):
        for member_name, member in get_members(target):
            member_ift_result = is_filter_type(member)

            if member_ift_result is True:
                logger.debug(
                    f"Registering extension filter "
                    f"{member.__module__}.{member.__name__}.",
                )

                yield member.__name__, member
            else:
                logger.debug(
                    f"Ignoring {target.__name__}.{member_name} ({member_ift_result})",
                )
    elif is_class(target):
        logger.debug(
            f"Ignoring {target.__module__}.{target.__name__} ({ift_result}).",
        )
    else:
        logger.debug(
            f"Ignoring {target!r} ({ift_result}).",
        )
