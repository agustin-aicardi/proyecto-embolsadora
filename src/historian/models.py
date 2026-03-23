from dataclasses import dataclass
from typing import Optional


@dataclass
class TagConfig:
    name: str
    type: str
    address: int
    unit: int = 1
    byteorder: str = "big"
    scale: Optional[float] = None