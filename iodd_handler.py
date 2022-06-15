"""Locate and handle IODD files for usage with a OPC-UA server.

A typical use case would be to have an IO-Link Master with some sensors connected to it,
and you want to find out which values of the sensor output are relevant to you. The
functions would then be executed in this order:
    1. find_connected_sensors -> Take found sensor names from here
    2. iodd_scraper -> List of IODD file locations
    3. iodd_parser -> Information about the sensor outputs
    4. iodd_to_value_index -> calculates the indices you need to pull the correct data
       from the OPC-UA server

Functions
---------
find_connected_sensors:
    Looks through the specified OPC-UA server for a number of connections to find any
    connected sensors
iodd_parser:
    Parses IODD xml files into dictionaries with relevant information regarding sensor
    output
iodd_scraper:
    Scrapes a local collection and IODDfinder for the desired IODD files
iodd_to_value_index:
    Transforms the bit length information to indices for use with the output from an
    OPC-UA server

"""
import json
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from asyncua import Client
from asyncua.ua.uaerrors._auto import BadNotConnected, BadNoData
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from iodd import IODD, InformationPoint


logging.basicConfig(level=logging.DEBUG)


async def find_connected_sensors(
    opcua_host: str, opcua_port: int, connections: int = 8
) -> list[dict]:
    """Find the sensors that are connected to the specified OPC-UA server.

    :param opcua_host: Host URL of the OPC-UA server
    :param opcua_port: Port of the OPC-UA server
    :param connections: Number of ports of the IO-Link master, defaults to 8
    :return: List of dictionaries containing port number and sensor names (if available)
    """
    async with Client(f"opc.tcp://{opcua_host}:{opcua_port}") as client:
        connected_sensors: list = []
        for i in range(1, connections + 1):
            node = client.get_node(f"ns=1;s=IOLM/Port {i}/Attached Device/Product Name")
            connected_sensors.append({"port": i, "name": None})
            try:
                sensor = await node.read_value()
                connected_sensors[-1]["name"] = sensor
                logging.debug(f"Sensor {sensor} connected to port {i}")
            except BadNotConnected:
                logging.debug(f"No sensor connected to port {i}")
            except BadNoData:
                logging.debug(
                    f"Sensor connected to port {i}, but name could not be read. "
                    "Might be due to non IO-Link sensor connection."
                )

    return connected_sensors


def iodd_parser(iodd: IODD) -> IODD:
    """Parse IODD file into easy to understand IODD dataclass.

    An IODD file is a *.xml file that describes an IO-Link sensor.

    :param iodd: IODD object containing the location of the IODD file
    :return: modified input IODD object with relevant information points
    """
    iodd_schema_loc = "{http://www.io-link.com/IODD/2010/10}"

    tree = ET.parse(iodd.iodd_file_location)
    root = tree.getroot()

    logging.debug(f"IODD file for {iodd.sensor_name} ready for parsing.")

    elements_with_unitcode = root.findall(f".//{iodd_schema_loc}*[@unitCode]")
    unitcodes_input = []
    for element in elements_with_unitcode:
        unitcode = element.get("unitCode")
        if unitcode not in unitcodes_input:
            unitcodes_input.append(unitcode)
    dict_unit_codes_SI = iodd_unitcodes(unitcodes_input=unitcodes_input)
    # DeviceFunction element can be used as root for search for records and menus
    device_function = root.find(
        f"./{iodd_schema_loc}ProfileBody/{iodd_schema_loc}DeviceFunction"
    )

    # Searching for the root of records, menus and texts is better for readability
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

    datatypes = device_function.find(f"./{iodd_schema_loc}DatatypeCollection")

    for idx, record in enumerate(records):
        name_node = record.find(f"./{iodd_schema_loc}Name")
        nameid = name_node.get("textId")
        text = texts.find(f"./{iodd_schema_loc}Text[@id='{nameid}']")
        name = text.get("value")
        bit_offset = int(record.get("bitOffset"))
        subindex = int(record.get("subindex"))

        # Some records might have a custom datatype, this accounts for that
        data = record.find(f"./{iodd_schema_loc}SimpleDatatype")
        if data is None:
            datatype_ref = record.find(f"./{iodd_schema_loc}DatatypeRef")
            datatype_id = datatype_ref.get("datatypeId")
            data = datatypes.find(f".{iodd_schema_loc}Datatype[@id='{datatype_id}']")

        # boolean like datatypes have no bit length in their attributes, but are
        # represented by a 0 or 1 -> bit length is 1
        bit_length = data.get("bitLength")
        if bit_length is None:
            bit_length = 1
        else:
            bit_length = int(bit_length)

        information_point = InformationPoint(
            name=name, bit_offset=bit_offset, bit_length=bit_length, subindex=subindex
        )

        valueRange = data.find(f"./{iodd_schema_loc}ValueRange")
        if valueRange is not None:
            low_val = int(valueRange.get("lowerValue"))
            up_val = int(valueRange.get("upperValue"))
            information_point.low_val = low_val
            information_point.up_val = up_val

        iodd.information_points.append(information_point)

    for menu in menus:
        if any(
            [
                re.search(f"^M_MR_SR_Observation(_[^_]*)?(_{unit})?$", menu.get("id"))
                for unit in dict_unit_codes_SI.keys()
            ]
        ):
            record_item_ref = menu.find(f"./{iodd_schema_loc}RecordItemRef")
            subindex = int(record_item_ref.get("subindex"))
            for idx, information_point in enumerate(iodd.information_points):
                if information_point.subindex == subindex:
                    gradient = record_item_ref.get("gradient")
                    iodd.information_points[idx].gradient = (
                        float(gradient) if gradient is not None else gradient
                    )
                    offset = record_item_ref.get("offset")
                    iodd.information_points[idx].offset = (
                        float(offset) if offset is not None else offset
                    )
                    iodd.information_points[idx].display_format = record_item_ref.get(
                        "displayFormat"
                    )
                    unitcode = record_item_ref.get("unitCode")
                    iodd.information_points[idx].unit_code = (
                        int(unitcode) if unitcode is not None else unitcode
                    )
                    iodd.information_points[idx].units = dict_unit_codes_SI[
                        int(unitcode) if unitcode is not None else unitcode
                    ]

    total_bit_length = int(records.get("bitLength"))
    iodd.total_bit_length = total_bit_length

    return iodd


def iodd_scraper(
    sensors: list | str,
    use_local: bool = True,
    iodd_folder: str = ".\\iodd",
) -> list[IODD]:
    r"""Scrape the IODD finder for the desired sensors IODD file(s).

    If the use_local option is set to False, this function will replace any existing
    IODD file with a new file.
    ***Important***: This currently relies on Chrome being installed -> should be
    noted somehow or checked in the function!

    :param sensors: Name of your sensor(s)
    :param use_local: Whether to use a local collection of IODD files, defaults to True
    :param iodd_folder: Location of local IODD file collection, defaults to ".\iodd"
    :return: List of IODD xml files
    """
    # TODO: Make sure the file we downloaded actually has the sensor in its variants
    cwd = os.getcwd()
    iodds = []

    if type(sensors) == str:
        sensors = [sensors]

    if not os.path.exists(iodd_folder):
        logging.debug(f"Folder {iodd_folder} doesn't exist and will be created.")
        os.mkdir(iodd_folder)

    if not os.path.exists(f"{cwd}\\.tmp"):
        logging.debug("Creating temporary directory to store downloaded files.")
        os.mkdir(f"{cwd}\\.tmp")

    # Configuring the browser used with Selenium
    browser_options = Options()
    browser_options.headless = True
    prefs = {"download.default_directory": f"{cwd}\\.tmp"}
    browser_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    browser_options.add_experimental_option("prefs", prefs)
    driver = None

    terms_accepted = False

    with open(f"{iodd_folder}\\iodd_collection_index.json", "r") as f:
        known_iodds = json.loads(f.read())

    for sensor in sensors:
        sensor_known = False
        for known_iodd in known_iodds:
            if sensor in known_iodd["family"]:
                if os.path.exists(known_iodd["file"]) and use_local:
                    logging.info(
                        f"IODD for {sensor} already exists in IODD collection."
                    )
                    iodds.append(
                        IODD(sensor_name=sensor, iodd_file_location=known_iodd["file"])
                    )
                    sensor_known = True
                    break
        if sensor_known:
            continue
        logging.info(
            f"IODD for {sensor} missing from IODD collection or to be"
            " replaced. Scraping IODDfinder."
        )
        # Only need to start the driver if it is actually necessary
        if driver is None:
            driver = webdriver.Chrome(
                service=Service(executable_path=ChromeDriverManager().install()),
                options=browser_options,
            )
            driver.implicitly_wait(10)

        # Scraping IODDfinder for the sensors IODD
        driver.get(
            "https://ioddfinder.io-link.com/productvariants/"
            f"search?productName=%22{sensor}%22"
        )

        # If the IODD is not available in IODDfinder, a text will be displayed instead
        # of the table -> Try find that text to see if the sensor was found
        try:
            driver.find_element(by=By.XPATH, value="//*[./text()='No data to display']")
            logging.warning(f"{sensor}:Couldn't find sensor in IODDfinder.")
            continue
        except NoSuchElementException:
            pass

        # If the IODD was found in IODDfinder, download it and process it
        download_button = driver.find_element(
            by=By.XPATH, value="//datatable-body-cell"
        )
        logging.debug(f'{sensor}:Found "Download" button')
        download_button.click()
        if not terms_accepted:
            accept_button = driver.find_element(
                by=By.XPATH, value="//*[./text()='Accept']"
            )
            logging.debug('Found "Accept" button')
            accept_button.click()
            terms_accepted = True
        while not os.path.exists(f"{cwd}\\.tmp\\iodd.zip"):
            logging.debug(f"{sensor}:Waiting for download to finish...")
            time.sleep(1)
        logging.debug(f"{sensor}:Download finished.")

        # Handling downloaded zip file
        with ZipFile(f"{cwd}\\.tmp\\iodd.zip") as archive:
            file_found = False
            for info in archive.infolist():
                if re.search("(IODD1.1.xml)", info.filename):
                    logging.debug(f"{sensor}:Found IODD file.")
                    file_found = True
                    if os.path.exists(f"{cwd}\\iodd\\{info.filename}"):
                        logging.debug(
                            f"{sensor}:IODD file already exists and will "
                            "be replaced."
                        )
                        os.remove(f"{cwd}\\iodd\\{info.filename}")
                    archive.extract(member=info.filename, path=".\\iodd\\")
                    iodds.append(
                        IODD(
                            sensor_name=sensor,
                            iodd_file_name=f"{cwd}\\iodd\\{info.filename}",
                        )
                    )
                    break
            if not file_found:
                logging.warning(f"{sensor}:Couldn't find IODD file in zip archive.")
        # Remove the zip file to avoid multiple files with hard to track names, e.g.
        # IODD (1).zip etc.
        os.remove(f"{cwd}\\.tmp\\iodd.zip")

    # Finally remove temporary directory stop the driver, and update the known iodds
    os.rmdir(f"{cwd}\\.tmp")
    try:
        # If the driver was never started, this will raise an error
        driver.quit()
    except AttributeError:
        logging.debug("Attempted to close driver, but driver was never started.")
    update_iodd_collection()
    return iodds


def iodd_to_value_index(parsed_iodd: IODD, block_length: int = 8) -> IODD:
    """Convert information about bit offset and length to useable indices.

    :param parsed_iodd: parsed IODD object
    :param block_length: length of one block of bits, defaults to 8
    :return: IODD object with value indices added
    """
    for idx, ip in enumerate(parsed_iodd.information_points):
        bit_offset = ip.bit_offset
        bit_length = ip.bit_length
        if (bit_length % block_length == 0) and (bit_length >= block_length):
            num_indices = int(bit_length / block_length)
        else:
            num_indices = 1

        value_indices: list[int] = []
        start_index = int(
            (parsed_iodd.total_bit_length - (bit_offset + bit_length)) / block_length
        )
        for index in range(start_index, start_index + num_indices):
            value_indices.append(index)
        parsed_iodd.information_points[idx].value_indices = value_indices

    return parsed_iodd


def iodd_unitcodes(
    unitcodes_input: list, loc: str = ".\\iodd\\IODD-StandardUnitDefinitions1.1.xml"
) -> list[dict]:
    r"""Associate unitcodes with their respective abbreviations.

    :param unitcodes_input: list of unitcodes used in a given IODD
    :param loc: location of the IODD-StandardUnitDefinitions*.xml file,
                defaults to ".\iodd\IODD-StandardUnitDefinitions1.1.xml"
    :return: list of dicts with used unitcodes
    """
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


def update_iodd_collection(iodd_collection_loc: str = "iodd"):
    """Update the IODD collection file.

    :param iodd_collection_loc: _description_, defaults to "iodd"
    """
    iodd_schema_loc = "{http://www.io-link.com/IODD/2010/10}"

    iodd_collection = [
        (os.path.join(os.getcwd(), iodd_collection_loc, file), file)
        for file in os.listdir(path=iodd_collection_loc)
    ]

    updated_iodd_collection: list[dict] = []
    for file in iodd_collection:
        if file[1] in [
            "iodd_collection_index.json",
            "IODD-StandardUnitDefinitions1.1.xml",
        ]:
            continue
        tree = ET.parse(source=file[0])
        root = tree.getroot()
        device_variants = root.findall(
            f"./{iodd_schema_loc}ProfileBody"
            f"/{iodd_schema_loc}DeviceIdentity"
            f"/{iodd_schema_loc}DeviceVariantCollection"
            f"/{iodd_schema_loc}DeviceVariant"
        )
        variants = [dv.get("productId") for dv in device_variants]
        updated_iodd_collection.append(
            {"family": variants, "file": f"{os.getcwd()}\\iodd\\{file[1]}"}
        )
    with open(
        os.path.join(iodd_collection_loc, "iodd_collection_index.json"), "w"
    ) as f:
        json.dump(updated_iodd_collection, f, indent=4)


# For testing, should be deleted at some point or moved to module description
from pprint import pprint

iodds = iodd_scraper(["OGH283"])
iodds = [iodd_parser(iodd) for iodd in iodds]
pprint(iodds[0].information_points[0])
iodds = [iodd_to_value_index(iodd) for iodd in iodds]
pprint(iodds[0].information_points[0])
