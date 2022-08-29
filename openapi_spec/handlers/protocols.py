from typing import TYPE_CHECKING
from typing import Optional

if TYPE_CHECKING:
    from typing_extensions import Protocol
    from typing_extensions import runtime_checkable
else:
    try:
        from typing import Protocol
        from typing import runtime_checkable
    except ImportError:
        from typing_extensions import Protocol
        from typing_extensions import runtime_checkable


@runtime_checkable
class SupportsRead(Protocol):
    def read(self, amount: Optional[int] = 0) -> str:
        ...
