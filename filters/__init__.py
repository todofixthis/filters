# http://stackoverflow.com/a/2073599/
from pkg_resources import require
__version__ = require('phx-filters')[0].version
del require

# Make the base filters accessible from the top level of the package.
# Note that the order is important here, due to dependencies.
from .base import *
from .handlers import *
from .macros import *
from .number import *
from .simple import *
from .complex import *
from .string import *

# Additional filters are loaded into a separate namespace, so that IDEs
# don't go insane.
from filters.extensions import FilterExtensionRegistry

ext = FilterExtensionRegistry()
del FilterExtensionRegistry
