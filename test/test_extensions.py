from unittest import TestCase

from filters.extensions import FilterExtensionRegistry
from filters.macros import FilterMacroType
from test import TestFilterAlpha, TestFilterBravo
from test.helper import DummyDistributionFinder


def setUpModule():
    # Inject a distribution that defines some entry points.
    DummyDistributionFinder.install()


def tearDownModule():
    DummyDistributionFinder.uninstall()


class FilterExtensionRegistryTestCase(TestCase):
    def test_happy_path(self):
        """
        Loading filters automatically via entry points.

        References:
          - /test/_support/filter_extension.egg-info/entry_points.txt
          - :py:func:`setUpModule`
        """
        # For this test, we will use a different entry point key, to
        # minimize the potential for side effects.
        registry = FilterExtensionRegistry('filters.extensions_test')

        # Note that the filters are registered using the entry point
        # names, which conventionally matches the class name (but it
        # doesn't strictly have to).
        alpha = registry.Alfred
        self.assertIs(alpha, TestFilterAlpha)

        # You can also instantiate filters using parameters.
        bravo = registry.Bruce(name='Batman')
        self.assertIsInstance(bravo, TestFilterBravo)
        self.assertEqual(bravo.name, 'Batman')

        # I couldn't find any Batman characters whose name begins with
        # C... and "Commissioner Gordon" doesn't count!
        charlie = registry.Catwoman
        # Note that :py:data:`test.TestFilterCharlie` is a filter
        # macro.
        self.assertTrue(issubclass(charlie, FilterMacroType))

        # Check that the correct number of extension filters were
        # registered.
        self.assertEqual(len(registry), 3)
