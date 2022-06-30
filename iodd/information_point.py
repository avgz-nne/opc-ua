from dataclasses import dataclass
from typing import Optional


@dataclass
class InformationPoint:
    """Dataclass to store information about an information point.

    An information point describes a singular output value of a sensor and how the raw
    data from the OPC-UA server needs to be processed.

    Note: Call convert_bounds() and convert_display_format() on the InformationPoint
    object when you have finished creating and filling it. Can't do that as a post_init
    function, because sometimes you may want to fill the object with the optional data
    at a later point.

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

    Methods
    -------

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

    def convert_bounds(self) -> None:
        """Convert some of the data to be more human-readable."""
        # convert lower and upper bounds to real values instead of byte values
        if (self.low_val is not None) and (self.gradient is not None) and (self.offset is not None):
            self.low_val = round(
                self.low_val * self.gradient + self.offset,
                self.display_format
            )
        else:
            self.low_val = -1
        if (self.up_val is not None) and (self.gradient is not None) and (self.offset is not None):
            self.up_val = round(
                self.up_val * self.gradient + self.offset,
                self.display_format
            )
        else:
            self.up_val = -1

    def convert_display_format(self) -> None:
        """Convert display format to integer.

        Display format comes in the form of "Dec.X", where X is the number of decimals
        Converting this into an int allows easier usage later for rounding
        """
        if self.display_format is not None:
            self.display_format = int(self.display_format.split(".")[1])

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
            byte_value = int.from_bytes(
                [byte_values[i] for i in self.value_indices],
                byteorder=byteorder,
                signed=signed,
            )
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

        value = int.from_bytes(
            [byte_values[i] for i in self.value_indices],
            byteorder=byteorder,
            signed=signed,
        ) * gradient + offset
        if self.display_format is not None:
            return round(value, self.display_format)
        else:
            return value
