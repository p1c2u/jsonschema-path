# Use CSafeFile if available
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yaml import SafeLoader
else:
    try:
        from yaml import CSafeLoader as SafeLoader
    except ImportError:
        from yaml import SafeLoader


__all__ = [
    "SafeLoader",
]
