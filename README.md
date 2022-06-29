# opc-ua

This repository is for having python opc ua scripts to get instpiration. Mainly for iiot box projects.

# Dashboard
The dashboard provides multiple views:
+ Home: A view to see which ports of the IoT box have a sensor connected to them. Also space for snarky text.
+ Monitor: A view to see basic graphs of the connected sensors. In the future, multiple tiled graphs should be displayed here for every sensor output
+ IODD collection: A view to quickly view some facts about the IODDs in the collection.
+ Settings: Currently not used, should in the future provide control about the OPC-UA server connection and the SQLite database (location, name etc.)

The dashboard is supposed to provide quick insights into the connected devices and their outputs. Since a good part of it is hardcoded, it might still be useful to set up a more flexible and advanced dashboard with Grafana or other software.

# IODD
IODD (or IO-Device Description) files describe how the IO-Link master handles the data coming from the sensor. It can also be used to get knowledge about how the nodes in the OPC-UA server should be handled (e.g. how to convert the raw bit values to actual values and what unit they are).

In order to keep things organized, this "library" will build up its own collection of IODD files that gets expanded everytime a sensor is connected that is unknown. The collection can be viewed in a more user-friendly way inside the dashboard.