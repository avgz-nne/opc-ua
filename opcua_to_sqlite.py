"""Script to log data from an OPC-UA server to a SQLite database.

This script does the following:
1. Registers some custom list like datatypes for SQLite
2. Sets up an SQLite database
3. Starts a connection with an OPC-UA server that is linked with an IO-Link master
4. Continuously checks the OPC-UA server for:
    4.1 Connectivity of sensors:
        if a sensor is connected to a port of the IO-Link master, the corresponding
        nodes of the OPC-UA server contain values -> this way we can check if there is a
        sensor connected, and if so, what its name is
         -> Writes this information to a table in the SQLite database
    4.2 Sensor values:
        Only the nodes that corresponds to a port we know has a sensor connected to it
        will be checked periodically
         -> Writes the values alongside time, name of the value, unit, lower and upper
            bounds to tables that contain information of a port
The reason we separate this process from the dashboard itself is: It doesn't work other-
wise, and I don't know why :)

Author: SPQL
Last changed: 29.06.2022
"""

import asyncio
from datetime import datetime
import logging
import time

from asyncua import Client
from asyncua.ua.uaerrors import BadNotConnected
import sqlite3

from iodd.errors import IODDNotFoundError
from iodd.iodd_collection_helpers import load_collection
from iodd.iodd import IODD
from sqlite_extension import FloatList, StringList, register_list_types


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("NNE-IoT-Dashboard")
register_list_types()

# TODO: currently this only handles one value/unit per information point, but sometimes
# there will be different values/units available (e.g. mm and in or deg C and deg F)


async def record_readings(
    cur: sqlite3.Cursor, con: sqlite3.Connection, ports: list[dict]
) -> None:
    """Insert the current values of the connected sensors into the SQLite db.

    :param cur: SQLite cursor object for querying
    :param con: SQLite connection object for querying
    :param ports: List of dictionaries corresponding to ports with asyncua nodes and
    their status as a bool
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    for port in ports:
        if port["connected"]:
            byte_values = await port["value_node"].read_value()
            information_points = []
            values = []
            lower_bounds = []
            upper_bounds = []
            units = []
            for ip in port["iodd"].information_points:
                information_points.append(ip.name)
                values.append(ip.byte_to_real_value(byte_values))
                lower_bounds.append(ip.low_val)
                upper_bounds.append(ip.up_val)
                units.append(ip.units)

            cur.execute(
                f"insert into port{port['id']} values (?, ?, ?, ?, ?, ?, ?)",
                (
                    now,
                    port["sensor"],
                    StringList(*information_points),
                    FloatList(*values),
                    FloatList(*lower_bounds),
                    FloatList(*upper_bounds),
                    StringList(*units),
                ),
            )
    con.commit()


def match_port_to_iodd(ports: list[dict], iodd_collection: list[IODD]) -> list[dict]:
    """Match the sensor connected to a port with the correct IODD from the collection.

    :param ports: list of dictionaries containing information about the ports
    :param iodd_collection: list of IODDs in the collection.
    :returns: modified version of ports with the correct IODD added
    """
    for i, port in enumerate(ports):
        if port["sensor"] is None:
            continue
        for iodd in iodd_collection:
            if (port["sensor"] is not None) and (port["sensor"] in iodd.family):
                ports[i]["iodd"] = iodd
        if ports[i]["iodd"] is None:
            raise IODDNotFoundError(port["sensor"])
    return ports


async def check_connections(
    cur: sqlite3.Cursor, con: sqlite3.Connection, ports: list[dict]
) -> tuple[list[dict], bool]:
    """Check the port connections of the IO-Link master.

    :param cur: SQLite cursor object for querying
    :param con: SQLite connection object for querying
    :param ports: List of dictionaries corresponding to ports with asyncua nodes and
    their status as a bool
    :returns: Modified version of the ports input with updated connection status and
    info whether any change happened
    """
    change_made = False
    for i, port in enumerate(ports):
        try:
            sensor_name = await port["name_node"].read_value()
            # If this didn't throw an error, that means that there is a sensor connected
            # We only need to update the table if the port previously didn't have any
            # sensor connected to it
            # Also, sometimes the sensor name is an empty string which we don't want
            if not port["connected"] and sensor_name != "":
                cur.execute(
                    "UPDATE connections SET connected = 'True', "
                    f"sensor = '{sensor_name}' WHERE id = {i+1}"
                )
                ports[i]["connected"] = True
                ports[i]["sensor"] = sensor_name
                change_made = True
                _logger.info(f"Connected sensor {sensor_name} to port {i+1}")
        except BadNotConnected:
            # We only need to update the table if the port previously had a sensor
            # connected to it
            if port["connected"]:
                cur.execute(
                    "UPDATE connections SET connected = 'False', "
                    f"sensor = 'N/A' WHERE id = {i+1}"
                )
                ports[i]["connected"] = False
                ports[i]["sensor"] = None
                change_made = True
                _logger.info(f"Disconnected sensor from port {i+1}")
    con.commit()
    return ports, change_made


def init_db(
    reset_connections_table: bool = True,
    reset_data_tables: list[int] = [1, 2, 3, 4, 5, 6, 7, 8],
) -> tuple[sqlite3.Cursor, sqlite3.Connection]:
    """Initialize the SQLite database and create a table for storing connection data.

    :param nameids: List of node IDs
    :returns: cursor and connection object to query the SQLite database with
    """
    con = sqlite3.connect("dashboard.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cur = con.cursor()

    # Handle connections table
    if reset_connections_table:
        try:
            cur.execute("DROP TABLE connections")
        except sqlite3.OperationalError as e:
            _logger.warning(
                'Attempt to drop table "connections" failed with error message: '
                f'"{e}"'
            )
    try:
        cur.execute(
            "CREATE TABLE connections (id integer, connected text, sensor text)"
        )
    except sqlite3.OperationalError as e:
        _logger.info(
            'Attempt to create table "connections" failed with error message: ' f'"{e}"'
        )

    # Handle data tables
    for i in reset_data_tables:
        try:
            cur.execute(f"DROP TABLE port{i}")
        except sqlite3.OperationalError as e:
            _logger.warning(
                f'Attempt to drop table "port{i}" failed with error message: ' f'"{e}"'
            )
    for i in range(1, 9):
        try:
            cur.execute(
                f"CREATE TABLE port{i}(time text, name text, ips stringlist, "
                "readings floatlist, lower_limits floatlist, upper_limits floatlist, "
                "units stringlist)"
            )
        except sqlite3.OperationalError as e:
            _logger.info(
                f'Attempt to create table "port{i}" failed with error message: '
                f'"{e}"'
            )

    cur.executemany(
        "INSERT INTO connections VALUES (?, ?, ?)",
        [(i, "False", "N/A") for i in range(1, 9)],
    )
    con.commit()
    return cur, con


async def main():
    """Track changes in port connections of IoT box.

    This explicitly does not use the subscription feature of asyncua because it seems to
    break when you subscribe to a node that has no value (-> BadNotConnected error)
    """
    cur, con = init_db()
    iodd_collection = load_collection()
    async with Client(url="opc.tcp://192.168.1.250:4840") as client:
        ports = [
            {
                "id": i,
                "sensor": None,
                "name_node": client.get_node(
                    f"ns=1;s=IOLM/Port {i}/Attached Device/Product Name"
                ),
                "value_node": client.get_node(
                    f"ns=1;s=IOLM/Port {i}/Attached Device/PDI Data Byte Array"
                ),
                "connected": False,
                "iodd": None,
            }
            for i in range(1, 9)
        ]
        while True:
            ports, change_made = await check_connections(cur, con, ports)
            if change_made:
                ports = match_port_to_iodd(ports, iodd_collection)
            await record_readings(cur, con, ports)
            time.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
