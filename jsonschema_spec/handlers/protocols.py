import sys
from typing import TYPE_CHECKING
from typing import Optional

if sys.version_info >= (3, 8):
    from typing import Protocol
    from typing import runtime_checkable
else:
    from typing_extensions import Protocol
    from typing_extensions import runtime_checkable


@runtime_checkable
class SupportsRead(Protocol):
    def read(self, amount: Optional[int] = 0) -> str:
        ...
