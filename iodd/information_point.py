from dataclasses import dataclass
from typing import Optional


@dataclass
class InformationPoint:
    """Dataclass to store information about an information point.

    An information point describes a singular output value of a sensor and how the raw
    data from the OPC-UA server needs to be processed.

    Attributes
    ----------
    name : str
        Name of the information point
    bit_offset : int
        offset from the right side of the bit-wise sensor output for a specific
        information point in bits
    bit_length : int
        length of the bit-wise sensor output for a specific information point in bits
    subindex : int
        used for indexing inside the IODD
    low_val : int
        lower bound for the bit values
    up_val : int
        upper bound for the bit values
    gradient : float
        factor for converting from bits to real values
    offset : float
        offset for converting from bits to real values
    display_format : str
        format for the real values
    unit_code : int
        IODD Standard Unit Definitions unit code for the unit of the real sensor output
    units : str
        abbreviation of the real sensor values unit
    value_indices : list[int]
        indices for getting the correct bit values from the sensor output
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
