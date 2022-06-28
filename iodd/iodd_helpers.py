import logging
import os
import xml.etree.ElementTree as ET


def iodd_unitcodes(
    unitcodes_input: list, loc: str = "iodd\\IODD-StandardUnitDefinitions1.1.xml"
) -> list[dict]:
    r"""Associate unitcodes with their respective abbreviations.

    :param unitcodes_input: list of unitcodes used in a given IODD
    :param loc: location of the IODD-StandardUnitDefinitions*.xml file,
                defaults to ".\iodd\IODD-StandardUnitDefinitions1.1.xml"
    :return: list of dicts with used unitcodes
    """
    if not os.path.exists(os.path.join(os.getcwd(), loc)):
        raise FileNotFoundError(
            "IODD StandardUnitDefinitions file not found at: "
            f"{os.path.join(os.getcwd(), loc)}"
        )
    tree = ET.parse(loc)
    root = tree.getroot()
    iodd_schema_loc = "{http://www.io-link.com/IODD/2010/10}"

    iodd_units_version = root.find(f"./{iodd_schema_loc}DocumentInfo")
    logging.debug(
        "IODD-StandardUnitDefinitions version " f"{iodd_units_version.get('version')}"
    )

    unitcodes_output = {}
    for unitcode in unitcodes_input:
        unit = root.find(
            f"./{iodd_schema_loc}UnitCollection"
            f"/{iodd_schema_loc}Unit[@code='{unitcode}']"
        )
        unitcodes_output[int(unit.get("code"))] = unit.get("abbr")

    # Some variables might have unitcode "None", therefore we will manually add an entry
    unitcodes_output[None] = "N/A"

    return unitcodes_output
