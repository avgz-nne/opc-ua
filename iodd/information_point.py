from dataclasses import dataclass
from typing import Optional

# TODO: low_val and up_val should be the actual lower and upper bounds, not the min and
# max in unconverted values
#   -> Could do this with post init function

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

    def byte_to_real_value(
        self, byte_values: list[int], byteorder: str = "big", signed: bool = True
    ):
        """Convert byte value of a sensor reading to real value.

        :param byte_values: List of byte values to convert
        :param byteorder: Indicate the order of byte values. If byte order is big, the
        most significant byte is at the beginning of the list, defaults to "big"
        :param signed: Whether the bytes are signed or not, defaults to True
        """
        # Special case for values that take up less than one 8-bit block
        if (self.bit_length % 8 != 0) and (len(self.value_indices) == 1):
            byte_value = int.from_bytes([byte_values[i] for i in self.value_indices], byteorder=byteorder, signed=signed)
            bit_list = [1 if byte_value & (1 << (7 - n)) else 0 for n in range(8)]
            start_index = 8 - (self.bit_offset + self.bit_length)
            end_index = start_index + self.bit_length
            return int("".join(str(i) for i in bit_list[start_index:end_index]), 2)
        
        if self.gradient is None:
            gradient = 1
        else:
            gradient = self.gradient

        if self.offset is None:
            offset = 0
        else:
            offset = self.offset

        return (
            int.from_bytes(
                [byte_values[i] for i in self.value_indices],
                byteorder=byteorder,
                signed=signed,
            ) * gradient + offset
        )
