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


async def find_connected_sensors(
    opcua_host: str, opcua_port: int, connections: int = 8
) -> list[dict]:
    """Find the sensors that are connected to the specified OPC-UA server.

    :param opcua_host: Host URL of the OPC-UA server
    :param opcua_port: Port of the OPC-UA server
    :param connections: Number of possible connections to the IO-Link master
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


def iodd_parser(filepath: str) -> tuple[list[dict], int]:
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
        f"./{iodd_schema_loc}ProfileBody/{iodd_schema_loc}DeviceFunction"
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

    datatypes = device_function.find(
        f"./{iodd_schema_loc}DatatypeCollection"
    )

    parsed_dicts: list[dict] = []
    for idx, record in enumerate(records):
        parsed_dicts.append({})
        name = record.find(f"./{iodd_schema_loc}Name")
        nameid = name.get("textId")
        text = texts.find(f"./{iodd_schema_loc}Text[@id='{nameid}']")
        parsed_dicts[idx]["name"] = text.get("value")
        parsed_dicts[idx]["bitOffset"] = record.get("bitOffset")
        parsed_dicts[idx]["subindex"] = record.get("subindex")
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
            bit_length = "1"
        parsed_dicts[idx]["bitLength"] = bit_length
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


def iodd_to_value_index(parsed_dicts: list[dict], total_bit_length: int) -> list[dict]:
    """Convert information about bit offset and length to useable indices.

    This function assumes that one "block" of information is 8 bits big.

    :param parsed_dicts: Dictionaries containing informaiton about bit offset and length
    :param total_bit_length: total amount of bits
    :return: list of dictionaries as given to the function with value indices added
    """
    block_length = 8
    max_index = int(total_bit_length / block_length)
    for idx, pd in enumerate(parsed_dicts):
        parsed_dicts[idx]["bitLength"] = (
            pd["bitLength"] if pd["bitLength"] is not None else "0"
        )

    for idx, pd in enumerate(parsed_dicts):
        bit_offset = int(pd["bitOffset"])
        bit_length = int(pd["bitLength"])
        if (bit_length % block_length == 0) and (bit_length >= block_length):
            num_indices = int(bit_length / block_length)
        else:
            num_indices = 1
        value_indices: list[int] = []
        start_index = int((total_bit_length - (bit_offset + bit_length)) / block_length)
        for index in range(start_index, start_index + num_indices):
            value_indices.append(index)
        print(value_indices, bit_length, bit_offset)


def iodd_scraper(
    sensors: list | str, use_local: bool = True, iodd_folder: str = ".\\iodd",
    driver_path: str = ".\\chromedriver.exe"
) -> list[str]:
    """Scrape the IODD finder for the desired sensors IODD file(s).

    If the use_local option is set to False, this function will replace any existing
    IODD file with a new file.
    ***Important***: This currently relies on Chrome being installed -> should be
    noted somehow or checked in the function!

    :param sensors: Name of your sensor(s)
    :param use_local: Whether to use a local collection of IODD files, defaults to True
    :param iodd_folder: Location of local IODD file collection, defaults to ".\\iodd"
    :param driver_path: Path to Chrome driver file
    :return: List of IODD xml files
    """
    cwd = os.getcwd()
    iodd_prefix = ""
    iodd_suffix = "_IODD.xml"
    iodds = []

    if not os.path.exists(driver_path):
        raise FileNotFoundError(
            "Couldn't locate chromedriver.exe at specified location."
        )

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

    for sensor in sensors:
        if os.path.exists(f"./iodd/{iodd_prefix}{sensor}{iodd_suffix}") and use_local:
            logging.info(
                f"IODD for {sensor} already exists in IODD collection."
            )
            iodds.append(f"{cwd}\\iodd\\{iodd_prefix}{sensor}{iodd_suffix}")
            continue
        logging.info(
            f"IODD for {sensor} missing from IODD collection or to be"
            " replaced. Scraping IODDfinder."
        )
        # Only need to start the driver if it is actually necessary
        if driver is None:
            driver = webdriver.Chrome(
                service=Service(driver_path), options=browser_options
            )
            driver.implicitly_wait(10)

        # Scraping IODDfinder for the sensors IODD
        driver.get(
            "https://ioddfinder.io-link.com/productvariants/"
            f"search?productName=%22{iodd_prefix}{sensor}%22"
        )

        # If the IODD is not available in IODDfinder, a text will be displayed instead
        # of the table -> Try find that text to see if the sensor was found
        try:
            driver.find_element(
                by=By.XPATH, value="//*[./text()='No data to display']"
            )
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
                    archive.extract(member=info.filename, path=".\\iodd\\")
                    if os.path.exists(
                        f"{cwd}\\iodd\\{iodd_prefix}{sensor}{iodd_suffix}"
                    ):
                        logging.debug(
                            f"{sensor}:IODD file already exists and will "
                            "be replaced."
                        )
                        os.remove(f"{cwd}\\iodd\\{iodd_prefix}{sensor}{iodd_suffix}")
                    try:
                        os.rename(
                            f"{cwd}\\iodd\\{info.filename}",
                            f"{cwd}\\iodd\\{iodd_prefix}{sensor}{iodd_suffix}",
                        )
                    except FileExistsError:
                        pass
                    iodds.append(f"{cwd}\\iodd\\{iodd_prefix}{sensor}{iodd_suffix}")
                    break
            if not file_found:
                logging.warning(
                    f"{sensor}:Couldn't find IODD file in zip archive."
                )
        # Remove the zip file to avoid multiple files with hard to track names, e.g.
        # IODD (1).zip etc.
        os.remove(f"{cwd}\\.tmp\\iodd.zip")

    # Finally remove temporary directory and stop the driver
    os.rmdir(f"{cwd}\\.tmp")
    try:
        # If the driver was never started, this will raise an error
        driver.quit()
    except AttributeError:
        logging.debug(f"Attempted to close driver, but driver was never started.")
    return iodds


myiodd = iodd_scraper(["CONTRINEX"])
for iodd in myiodd:
    dicts, bits = iodd_parser(iodd)
    for d in dicts:
        #iodd_to_value_index([d], 160)
        print(d)
