from dataclasses import dataclass, field
import logging
import re
import xml.etree.ElementTree as ET

from iodd.information_point import InformationPoint
from iodd.iodd_helpers import iodd_unitcodes


@dataclass
class IODD:
    """Dataclass to store information about IODD files and their contents.

    Attributes
    ----------
    iodd_file_location : str
        Location of the IODD file
    family : list[str]
        Name of the sensor which is part of the IODD file
    information_points : list[InformationPoint]
        List of InformationPoint objects that are part of the sensor/IODD
    total_bit_length : int
        bit length of the sensor output
    """

    iodd_file_location: str
    family: list[str] = field(default_factory=list)
    information_points: list[InformationPoint] = field(default_factory=list)
    total_bit_length: int = None
    iodd_schema = "{http://www.io-link.com/IODD/2010/10}"

    def __post_init__(self) -> None:
        """Parse data from the IODD file specified in the location variable."""
        tree = ET.parse(self.iodd_file_location)
        root = tree.getroot()

        device_variants = root.findall(
            f"./{self.iodd_schema}ProfileBody"
            f"/{self.iodd_schema}DeviceIdentity"
            f"/{self.iodd_schema}DeviceVariantCollection"
            f"/{self.iodd_schema}DeviceVariant"
        )
        variants = [dv.get("productId") for dv in device_variants]
        self.family = variants

        records = root.find(
            f"./{self.iodd_schema}ProfileBody"
            f"/{self.iodd_schema}DeviceFunction"
            f"/{self.iodd_schema}ProcessDataCollection"
            f"/{self.iodd_schema}ProcessData"
            f"/{self.iodd_schema}ProcessDataIn"
            f"/{self.iodd_schema}Datatype"
        )
        total_bit_length = int(records.get("bitLength"))
        self.total_bit_length = total_bit_length
        self.parse_information_points(root)

    def parse_information_points(self, root: ET) -> None:
        """Parse information points from IODD file to IODD object."""
        elements_with_unitcode = root.findall(f".//{self.iodd_schema}*[@unitCode]")
        unitcodes_input = []
        for element in elements_with_unitcode:
            unitcode = element.get("unitCode")
            if unitcode not in unitcodes_input:
                unitcodes_input.append(unitcode)
        dict_unit_codes_SI = iodd_unitcodes(unitcodes_input=unitcodes_input)
        # DeviceFunction element can be used as root for search for records and menus
        device_function = root.find(
            f"./{self.iodd_schema}ProfileBody/{self.iodd_schema}DeviceFunction"
        )

        # Searching for the root of records, menus and texts is better for readability
        records = device_function.find(
            f"./{self.iodd_schema}ProcessDataCollection"
            f"/{self.iodd_schema}ProcessData"
            f"/{self.iodd_schema}ProcessDataIn"
            f"/{self.iodd_schema}Datatype"
        )

        menus = device_function.findall(
            f"./{self.iodd_schema}UserInterface"
            f"/{self.iodd_schema}MenuCollection"
            f"/{self.iodd_schema}Menu"
        )

        texts = root.find(
            f"./{self.iodd_schema}ExternalTextCollection"
            f"/{self.iodd_schema}PrimaryLanguage"
        )

        datatypes = device_function.find(f"./{self.iodd_schema}DatatypeCollection")

        for idx, record in enumerate(records):
            name_node = record.find(f"./{self.iodd_schema}Name")
            nameid = name_node.get("textId")
            text = texts.find(f"./{self.iodd_schema}Text[@id='{nameid}']")
            name = text.get("value")
            bit_offset = int(record.get("bitOffset"))
            subindex = int(record.get("subindex"))

            # Some records might have a custom datatype, this accounts for that
            data = record.find(f"./{self.iodd_schema}SimpleDatatype")
            if data is None:
                datatype_ref = record.find(f"./{self.iodd_schema}DatatypeRef")
                datatype_id = datatype_ref.get("datatypeId")
                data = datatypes.find(
                    f".{self.iodd_schema}Datatype[@id='{datatype_id}']"
                )

            # boolean like datatypes have no bit length in their attributes, but are
            # represented by a 0 or 1 -> bit length is 1
            bit_length = data.get("bitLength")
            if bit_length is None:
                bit_length = 1
            else:
                bit_length = int(bit_length)

            information_point = InformationPoint(
                name=name,
                bit_offset=bit_offset,
                bit_length=bit_length,
                subindex=subindex,
            )

            valueRange = data.find(f"./{self.iodd_schema}ValueRange")
            if valueRange is not None:
                low_val = int(valueRange.get("lowerValue"))
                up_val = int(valueRange.get("upperValue"))
                information_point.low_val = low_val
                information_point.up_val = up_val

            self.information_points.append(information_point)
        for ip in self.information_points:
            logging.info(f"{ip.name}, {ip.bit_offset}")
        for menu in menus:
            if any(
                [
                    re.search(
                        f"^M_MR_SR_Observation(_[^_]*)?(_{unit})?$", menu.get("id")
                    )
                    for unit in dict_unit_codes_SI.keys()
                ]
            ):
                logging.info(f"Menu: {menu.get('id')}")
                record_item_ref = menu.find(f"./{self.iodd_schema}RecordItemRef")
                if record_item_ref is None:
                    continue
                subindex = int(record_item_ref.get("subindex"))
                for idx, information_point in enumerate(self.information_points):
                    if information_point.subindex == subindex:
                        gradient = record_item_ref.get("gradient")
                        self.information_points[idx].gradient = (
                            float(gradient) if gradient is not None else gradient
                        )
                        offset = record_item_ref.get("offset")
                        self.information_points[idx].offset = (
                            float(offset) if offset is not None else offset
                        )
                        self.information_points[
                            idx
                        ].display_format = record_item_ref.get("displayFormat")
                        unitcode = record_item_ref.get("unitCode")
                        self.information_points[idx].unit_code = (
                            int(unitcode) if unitcode is not None else unitcode
                        )
                        self.information_points[idx].units = dict_unit_codes_SI[
                            int(unitcode) if unitcode is not None else unitcode
                        ]
        for i, _ in enumerate(self.information_points):
            self.information_points[i].convert_display_format()
            self.information_points[i].convert_bounds()
        self.iodd_to_value_index()

    def iodd_to_value_index(self, block_length: int = 8) -> None:
        """Convert information about bit offset and length to useable indices.

        :param block_length: length of one block of bits, defaults to 8
        :return: IODD object with value indices added
        """
        for idx, ip in enumerate(self.information_points):
            bit_offset = ip.bit_offset
            bit_length = ip.bit_length
            if (bit_length % block_length == 0) and (bit_length >= block_length):
                num_indices = int(bit_length / block_length)
            else:
                num_indices = 1

            value_indices: list[int] = []
            start_index = int(
                (self.total_bit_length - (bit_offset + bit_length)) / block_length
            )
            for index in range(start_index, start_index + num_indices):
                value_indices.append(index)
            self.information_points[idx].value_indices = value_indices
