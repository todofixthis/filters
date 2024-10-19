# Make the base filters accessible from the top level of the package.
# Note that the order is important here, due to dependencies.
# Additional filters are loaded into a separate namespace, so that IDEs
# don't go insane.
from .base import Type
from .complex import (
    FilterMapper,
    FilterRepeater,
    FilterSwitch,
    NamedTuple,
)
from .extensions import FilterExtensionRegistry
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
    Unicode,
    Uuid,
)

__all__ = [
    "Array",
    "Base64Decode",
    "ByteArray",
    "ByteString",
    "Call",
    "CaseFold",
    "Choice",
    "Date",
    "Datetime",
    "Decimal",
    "Empty",
    "FilterMapper",
    "FilterRepeater",
    "FilterSwitch",
    "Int",
    "IpAddress",
    "Item",
    "JsonDecode",
    "Length",
    "Max",
    "MaxBytes",
    "MaxChars",
    "MaxLength",
    "Min",
    "MinLength",
    "NamedTuple",
    "NoOp",
    "NotEmpty",
    "Omit",
    "Optional",
    "Pick",
    "Regex",
    "Required",
    "Round",
    "Split",
    "Strip",
    "Type",
    "Unicode",
    "Uuid",
    "ext",
]

# Initialise extensions namespace.
ext = FilterExtensionRegistry()
del FilterExtensionRegistry
