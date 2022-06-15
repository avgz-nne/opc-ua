from dataclasses import dataclass
from typing import Optional


@dataclass
class InformationPoint:
    """Dataclass to store information about an information point.

    An information point describes a singular output value of a sensor and how the raw
    data from the OPC-UA server needs to be processed.
    """

    name: str
    bitOffset: int
    subindex: int
    bitLength: int
    low_val: Optional[int]
    up_val: Optional[int]
    gradient: Optional[float]
    display_format: Optional[str]
    unit_code: Optional[int]
    units: Optional[str]
    value_indices: list[int]


@dataclass
class IODD:
    """Dataclass to store information about IODD files and their contents."""

    sensor_name: str
    iodd_file_name: str
    information_point: InformationPoint
