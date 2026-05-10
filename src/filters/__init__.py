# Make the base filters accessible from the top level of the package.
# Note that the order is important here, due to dependencies.

__all__ = [
    # base
    "BaseFilter",
    "BaseInvalidValueHandler",
    "ExceptionHandler",
    "FilterChain",
    "FilterCompatible",
    "FilterError",
    "FilterMeta",
    "Type",
    # handlers
    "FilterMessage",
    "FilterRunner",
    "LogHandler",
    "MemoryHandler",
    # macros
    "FilterMacroType",
    "filter_macro",
    # number
    "Decimal",
    "Int",
    "Max",
    "Min",
    "Round",
    # simple
    "Array",
    "ByteArray",
    "Call",
    "Date",
    "Datetime",
    "Empty",
    "Item",
    "Length",
    "MaxLength",
    "MinLength",
    "NoOp",
    "NotEmpty",
    "Omit",
    "Optional",
    "Pick",
    "Required",
    # complex
    "FilterMapper",
    "FilterRepeater",
    "FilterSwitch",
    "NamedTuple",
    # string
    "Base64Decode",
    "ByteString",
    "CaseFold",
    "Choice",
    "IpAddress",
    "JsonDecode",
    "MaxBytes",
    "MaxChars",
    "Regex",
    "Split",
    "Strip",
    "TomlDecode",
    "Unicode",
    "Uuid",
    # extensions
    "ext",
]
from .base import (
    BaseFilter,
    BaseInvalidValueHandler,
    ExceptionHandler,
    FilterChain,
    FilterCompatible,
    FilterError,
    FilterMeta,
    Type,
)
from .handlers import (
    FilterMessage,
    FilterRunner,
    LogHandler,
    MemoryHandler,
)
from .macros import (
    FilterMacroType,
    filter_macro,
)
from .number import (
    Decimal,
    Int,
    Max,
    Min,
    Round,
)
from .simple import (
    Array,
    ByteArray,
    Call,
    Date,
    Datetime,
    Empty,
    Item,
    Length,
    MaxLength,
    MinLength,
    NoOp,
    NotEmpty,
    Omit,
    Optional,
    Pick,
    Required,
)
from .complex import (
    FilterMapper,
    FilterRepeater,
    FilterSwitch,
    NamedTuple,
)
from .string import (
    Base64Decode,
    ByteString,
    CaseFold,
    Choice,
    IpAddress,
    JsonDecode,
    MaxBytes,
    MaxChars,
    Regex,
    Split,
    Strip,
    TomlDecode,
    Unicode,
    Uuid,
)

# Additional filters are loaded into a separate namespace, so that IDEs
# don't get overwhelmed.
from filters.extensions import FilterExtensionRegistry

ext = FilterExtensionRegistry()
del FilterExtensionRegistry
