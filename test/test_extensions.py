from filters.extensions import FilterExtensionRegistry
from filters.macros import FilterMacroType
from test import FilterAlpha, FilterBravo
from test.helper import DummyDistributionFinder


def setup_module():
    """Inject a distribution that defines some entry points."""
    DummyDistributionFinder.install()


def teardown_module():
    """Remove the injected distribution."""
    DummyDistributionFinder.uninstall()


def test_filter_extension_registry_happy_path():
    """
    Loading filters automatically via entry points.

    References:
      - /test/_support/filter_extension.egg-info/entry_points.txt
      - :py:func:`setup_module`
    """
    # For this test, we will use a different entry point key, to
    # minimise the potential for side effects.
    registry = FilterExtensionRegistry("filters.extensions_test")

    # Note that the filters are registered using the entry point
    # names, which conventionally matches the class name (but it
    # doesn't strictly have to).
    alpha = registry.Alfred
    assert alpha is FilterAlpha

    # You can also instantiate filters using parameters.
    bravo = registry.Bruce(name="Batman")
    assert isinstance(bravo, FilterBravo)
    assert bravo.name == "Batman"

    # I couldn't find any Batman characters whose name begins with
    # C... and "Commissioner Gordon" doesn't count!
    charlie = registry.Catwoman
    # Note that :py:data:`test.TestFilterCharlie` is a filter
    # macro.
    assert issubclass(charlie, FilterMacroType)

    # Check that the correct number of extension filters were
    # registered.
    assert len(registry) == 3
