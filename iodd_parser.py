import re
import xml.etree.ElementTree as ET
import logging

logging.basicConfig(level=logging.INFO)


def iodd_parser(filepath) -> tuple[list[dict], int]:
    """Parse IODD file into easy to understand dictionaries.

    An IODD file is a *.xml file that describes an IO-Link sensor.

    :param filepath: Path to the *.xml IODD file you want to parse.
    :return: List of dictionaries describing each output the sensor has.
    """
    iodd_schema_loc = "{http://www.io-link.com/IODD/2010/10}"

    # Should get this from elsewhere and not hardcode it
    dict_unit_codes_SI = {
        "1000": "K degrees",
        "1001": "C degrees",
        "1010": "meters",
        "1023": "m2",
        "1034": "m3",
        "1054": "s",
        "1061": "m/s",
        "1076": "m/s2",
    }

    tree = ET.parse(filepath)
    root = tree.getroot()

    # DeviceFunction element can be used as root for search for records and menus
    device_function = root.find(
        f"./{iodd_schema_loc}ProfileBody" f"/{iodd_schema_loc}DeviceFunction"
    )

    records = device_function.find(
        f"./{iodd_schema_loc}ProcessDataCollection"
        f"/{iodd_schema_loc}ProcessData"
        f"/{iodd_schema_loc}ProcessDataIn"
        f"/{iodd_schema_loc}Datatype"
    )

    menus = device_function.findall(
        f"./{iodd_schema_loc}UserInterface"
        f"/{iodd_schema_loc}MenuCollection"
        f"/{iodd_schema_loc}Menu"
    )

    texts = root.find(
        f"./{iodd_schema_loc}ExternalTextCollection"
        f"/{iodd_schema_loc}PrimaryLanguage"
    )

    parsed_dicts: list[dict] = []
    for idx, record in enumerate(records):
        parsed_dicts.append({})
        data = record.find(f"./{iodd_schema_loc}SimpleDatatype")
        name = record.find(f"./{iodd_schema_loc}Name")
        nameid = name.get("textId")
        text = texts.find(f"./{iodd_schema_loc}Text[@id='{nameid}']")
        parsed_dicts[idx]["name"] = text.get("value")
        parsed_dicts[idx]["bitOffset"] = record.get("bitOffset")
        parsed_dicts[idx]["subindex"] = record.get("subindex")
        parsed_dicts[idx]["bitLength"] = data.get("bitLength")
        valueRange = data.find(f"./{iodd_schema_loc}ValueRange")
        if valueRange is not None:
            parsed_dicts[idx]["low_val"] = valueRange.get("lowerValue")
            parsed_dicts[idx]["up_val"] = valueRange.get("upperValue")

    for menu in menus:
        for unit in dict_unit_codes_SI.keys():
            if re.search(f"^M_MR_SR_Observation_.*{unit}$", menu.get("id")):
                record = menu.find(f"./{iodd_schema_loc}RecordItemRef")
                subindex = record.get("subindex")
                for parsed_dict in parsed_dicts:
                    if parsed_dict["subindex"] == subindex:
                        parsed_dict["gradient"] = record.get("gradient")
                        parsed_dict["offset"] = record.get("offset")
                        parsed_dict["displayFormat"] = record.get("displayFormat")
                        parsed_dict["unitCode"] = record.get("unitCode")
                        parsed_dict["units"] = dict_unit_codes_SI[
                            record.get("unitCode")
                        ]

    total_bit_length = int(records.get("bitLength"))

    return parsed_dicts, total_bit_length


def iodd_to_value_index(parsed_dicts, total_bit_length) -> list[dict]:
    for idx, pd in enumerate(parsed_dicts):
        parsed_dicts[idx]["bitLength"] = (
            pd["bitLength"] if pd["bitLength"] is not None else "0"
        )
    parsed_dicts = sorted(parsed_dicts, key=lambda d: d["subindex"])
    current_value_index: int = 0
    for idx, pd in enumerate(parsed_dicts):
        bit_offset = int(pd["bitOffset"])
        value_indices: list[int] = []
        while total_bit_length > bit_offset:
            value_indices.append(current_value_index)
            total_bit_length -= 8
            current_value_index += 1
        parsed_dicts[idx]["valueIndices"] = value_indices
        logging.info(
            f"{pd['name']}, {pd['valueIndices']}, {pd['bitLength']}, {pd['bitOffset']}"
        )

    # return sorted_dicts


parsed_dicts, total_bits = iodd_parser("ifm-vvb020.xml")
print(iodd_to_value_index(parsed_dicts, total_bits))
