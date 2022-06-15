from dataclasses import dataclass, field
from typing import Optional


@dataclass
class InformationPoint:
    """Dataclass to store information about an information point.

    An information point describes a singular output value of a sensor and how the raw
    data from the OPC-UA server needs to be processed.
    """

    name: str
    bit_offset: int
    bit_length: int
    subindex: int
    low_val: Optional[int] = None
    up_val: Optional[int] = None
    gradient: Optional[float] = None
    offset: Optional[float] = None
    display_format: Optional[str] = None
    unit_code: Optional[int] = None
    units: Optional[str] = None
    value_indices: list[int] = None


@dataclass
class IODD:
    """Dataclass to store information about IODD files and their contents."""

    sensor_name: str
    iodd_file_location: str
    information_points: list[InformationPoint] = field(default_factory=list)
    total_bit_length: int = None
