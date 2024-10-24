from unittest import TestCase

from filters.extensions import FilterExtensionRegistry
from test import FilterAlpha, FilterBravo
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
        registry = FilterExtensionRegistry("filters.extensions_test")

        # Note that the filters are registered using the entry point
        # names, which conventionally matches the class name (but it
        # doesn't strictly have to).
        alpha = registry.Alfred
        self.assertIs(alpha, FilterAlpha)

        # You can also instantiate filters using parameters.
        bravo = registry.Bruce(name="Batman")
        self.assertIsInstance(bravo, FilterBravo)
        self.assertEqual(bravo.name, "Batman")

        # Check that the correct number of extension filters were
        # registered.
        self.assertEqual(len(registry), 2)
