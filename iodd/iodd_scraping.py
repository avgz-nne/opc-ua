"""Locate and handle IODD files for usage with a OPC-UA server.

A typical use case would be to have an IO-Link Master with some sensors connected to it,
and you want to find out which values of the sensor output are relevant to you. The
functions would then be executed in this order:
    1. find_connected_sensors
    2. iodd_scraper
    3. iodd_parser
    4. iodd_to_value_index

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
from zipfile import ZipFile

from asyncua import Client
from asyncua.ua.uaerrors._auto import BadNotConnected, BadNoData
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from iodd import IODD
from iodd_help_functions import update_iodd_collection

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


def iodd_scraper(
    sensors: list | str,
    use_local: bool = True,
    collection_folder: str = "collection",
) -> list[IODD]:
    r"""Scrape the IODD finder for the desired sensors IODD file(s).

    If the use_local option is set to False, this function will replace any existing
    IODD file with a new file.
    ***Important***: This currently relies on Chrome being installed -> should be
    noted somehow or checked in the function!

    :param sensors: Name of your sensor(s)
    :param use_local: Whether to use a local collection of IODD files, defaults to True
    :param collection_folder: IODD file collection location, defaults to "collection"
    :return: List of IODD xml files
    """
    cwd = os.getcwd()
    iodds: list[IODD] = []

    if type(sensors) == str:
        sensors = [sensors]

    if not os.path.exists(os.path.join(cwd, "iodd", collection_folder)):
        logging.debug(f"Folder {collection_folder} doesn't exist and will be created.")
        os.mkdir(collection_folder)

    if not os.path.exists(os.path.join(cwd, ".tmp")):
        logging.debug("Creating temporary directory to store downloaded files.")
        os.mkdir(os.path.join(cwd, ".tmp"))

    # Configuring the browser used with Selenium
    browser_options = Options()
    browser_options.headless = True
    prefs = {"download.default_directory": os.path.join(cwd, ".tmp")}
    browser_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    browser_options.add_experimental_option("prefs", prefs)
    driver = None

    terms_accepted = False

    with open(
        os.path.join(cwd, "iodd", collection_folder, "iodd_collection_index.json"), "r"
    ) as f:
        iodd_collection = json.loads(f.read())

    for sensor in sensors:
        # If the sensor is already in our collection and we want to reuse it, or if we
        # have multiple of the same sensor connected
        sensor_known = False
        for iodd_collection_entry in iodd_collection:
            if sensor in iodd_collection_entry["family"]:
                if os.path.exists(iodd_collection_entry["file"]) and use_local:
                    logging.info(
                        f"IODD for {sensor} already exists in IODD collection."
                    )
                    sensor_known = True
                    break
        for iodd in iodds:
            if sensor in iodd.family:
                logging.info(f"Sensor {sensor} is part of a previously scraped IODD")
                sensor_known = True
                break
        if sensor_known:
            try:
                iodds.append(
                    IODD(
                        iodd_file_location=iodd_collection_entry["file"]
                    )
                )
            except Exception:
                pass
            try:
                iodds.append(
                    IODD(
                        iodd_file_location=iodd.iodd_file_location
                    )
                )
            except Exception:
                pass
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
        while not os.path.exists(os.path.join(cwd, ".tmp", "iodd.zip")):
            logging.debug(f"{sensor}:Waiting for download to finish...")
            time.sleep(1)
        logging.debug(f"{sensor}:Download finished.")

        # Handling downloaded zip file
        with ZipFile(os.path.join(cwd, ".tmp", "iodd.zip")) as archive:
            file_found = False
            for info in archive.infolist():
                if re.search("(IODD1.1.xml)", info.filename):
                    logging.debug(f"{sensor}:Found IODD file.")
                    file_found = True
                    if os.path.exists(os.path.join(cwd, "iodd", collection_folder, info.filename)):
                        logging.debug(
                            f"{sensor}:IODD file already exists and will "
                            "be replaced."
                        )
                        os.remove(os.path.join(cwd, "iodd", collection_folder, info.filename))
                    archive.extract(
                        member=info.filename,
                        path=os.path.join(cwd, "iodd", collection_folder)
                    )
                    iodds.append(
                        IODD(
                            iodd_file_location=os.path.join(cwd, "iodd", collection_folder, info.filename),
                        )
                    )
                    break
            if not file_found:
                logging.warning(f"{sensor}:Couldn't find IODD file in zip archive.")
        # Remove the zip file to avoid multiple files with hard to track names, e.g.
        # IODD (1).zip etc.
        os.remove(os.path.join(cwd, ".tmp", "iodd.zip"))

    # Finally remove temporary directory stop the driver, and update the known iodds
    os.rmdir(os.path.join(cwd, ".tmp"))
    try:
        # If the driver was never started, this will raise an error
        driver.quit()
    except AttributeError:
        logging.debug("Attempted to close driver, but driver was never started.")
    update_iodd_collection()
    return iodds

 
# For testing, should be deleted at some point or moved to module description
from pprint import pprint

iodds = iodd_scraper(["OGH283", "O6H707", "O6H707"])
pprint(iodds)
#iodds = [iodd_to_value_index(iodd) for iodd in iodds]
