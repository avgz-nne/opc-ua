import asyncio
import logging
from pprint import pprint
import time

from asyncua import Client
from asyncua.ua.uaerrors import BadNotConnected
import sqlite3

from iodd.iodd_collection_helpers import load_collection
from iodd.iodd import IODD


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("NNE-IoT-Dashboard")


async def record_readings(
    client: Client, cur: sqlite3.Cursor, con: sqlite3.Connection, ports: list[dict]
):
    for i, port in enumerate(ports):
        if port["connected"]:
            byte_values = await port["value_node"].read_value()
            values = []
            for ip in port["iodd"].information_points:
                value = ip.byte_to_real_value(byte_values)
                values.append({"name": ip.name, "value": value, "unit": ip.units})
            pprint(values)


def match_port_to_iodd(ports: list[dict], iodd_collection: list[IODD]) -> list[dict]:
    for i, port in enumerate(ports):
        for iodd in iodd_collection:
            if (port["sensor"] is not None) and (port["sensor"] in iodd.family):
                ports[i]["iodd"] = iodd
    return ports


async def check_connections(
    cur: sqlite3.Cursor, con: sqlite3.Connection, ports: list[dict]
) -> tuple[list[dict], bool]:
    """Check the port connections of the IO-Link master.

    :param cur: SQLite cursor object for querying
    :param con: SQLite connection object for querying
    :param ports: List of dictionaries corresponding to ports with asyncua nodes and their status as a bool
    :returns: Modified version of the ports input with updated connection status and info whether any change happened
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
    reset_connections_table: bool = True, reset_data_tables: list[int] = []
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
            "CREATE TABLE connections " "(id integer, connected text, sensor text)"
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
                f"CREATE TABLE port{i} "
                "(timestamp text, sensor text, readings text, units text)"
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
                "id": i + 1,
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
            await record_readings(client, cur, con, ports)
            time.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
