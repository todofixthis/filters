import sys
from importlib.metadata import DistributionFinder, PathDistribution
from os import path
from pathlib import Path

_DEFAULT_CONTEXT = DistributionFinder.Context()


class DummyDistributionFinder(DistributionFinder):
    """
    Injects a dummy distribution into the meta path finder, so that we can
    pretend like it's been pip installed during unit tests (i.e., so that we
    can test ``FilterExtensionRegistry``), without polluting the persistent
    virtualenv.
    """

    DUMMY_PACKAGE_DIR = "filter_extension.egg-info"

    @classmethod
    def install(cls) -> None:
        # If we've already installed an instance of the class, then
        # something is probably wrong with our tests.
        if any(isinstance(finder, cls) for finder in sys.meta_path):
            raise ValueError(f"{cls.__name__} is already installed")

        sys.meta_path.append(cls())

    @classmethod
    def uninstall(cls) -> None:
        for i, finder in enumerate(sys.meta_path):
            if isinstance(finder, cls):
                sys.meta_path.pop(i)
                return
        # If we didn't find an installed instance of the class, then
        # something is probably wrong with our tests.
        raise ValueError(f"{cls.__name__} was not installed")

    def find_distributions(
        self, context: DistributionFinder.Context = _DEFAULT_CONTEXT
    ) -> list[PathDistribution]:
        return [
            PathDistribution(
                Path(path.join(path.dirname(__file__), self.DUMMY_PACKAGE_DIR))
            )
        ]
