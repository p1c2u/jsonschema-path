from typing import Optional
from typing import Protocol
from typing import runtime_checkable


@runtime_checkable
class SupportsRead(Protocol):
    def read(self, amount: Optional[int] = 0) -> str:
        ...
