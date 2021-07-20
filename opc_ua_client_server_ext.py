import asyncio
import logging
import time

from asyncua import Client, Server
from asyncua import ua

_logger = logging.getLogger('asyncua')

async def client_reader(client, idx, nodeid):
        print(idx, nodeid)
        var = client.get_node(ua.NodeId(nodeid, idx))
        data = await var.read_value()
        print('byte data is')
        print(data)
        return data
def data_converter(bytes_raw, dict_converter):
        data_bytes = bytes_raw[dict_converter["start"],dict_converter["end"]]
        data = int.from_bytes(data_bytes, byteorder='big',signed=True)
        value = data * dict_converter["gradient"]
        return value

async def main():
    nsidx = 6
    nodeids = [32824, 98360, 163896] #[pressure pipe, #pressure tan level, temperature pipe]
    dict_conv1 = {"nbytes":4, "rbits":4, "start":0 , "end":2, "gradient":0.01, "conversion": 1}
    dict_conv2 = {"nbytes":4, "rbits":0, "start":0 , "end":2, "gradient":0.01, "conversion": 0.0254}
    dict_conv3 = {"nbytes":2, "rbits":0, "start":0 , "end":2, "gradient":0.1, "conversion": 1}
    converters = [dict_conv1 , dict_conv2, dict_conv3]
    # setup our server
    server = Server()
    await server.init()
    server.set_endpoint('opc.tcp://192.168.1.10:4840/nne_unibio/server/')
     # setup our own namespace, not really necessary but should as spec
    uri = 'http://nne.unibio'
    idx = await server.register_namespace(uri)
    # populating our address space
    # server.nodes, contains links to very common nodes like objects and root
    coretigo_url = 'opc.tcp://192.168.1.100:4840/'
    client = Client(url=coretigo_url)
    async with server and client:
        myobj = await server.nodes.objects.add_object(idx, 'CIP_DATA')
        port1_PI = await myobj.add_variable(idx, 'Port 1', 0.0)
        port2_PI = await myobj.add_variable(idx, 'Port 2', 0.0)
        port3_PI = await myobj.add_variable(idx, 'Port 3', 0.0)
        #port4_PI = await myobj.add_variable(idx, 'Port 4', 0.0)
        ports = [port1_PI, port2_PI, port3_PI]
        while True:
            for nodeid, dict_converter, port in zip(nodeids, converters, ports):
                var = client.get_node(ua.NodeId(nodeid, nsidx))
                data_raw = await var.read_value()
                data_bytes = data_raw[dict_converter["start"]:dict_converter["end"]]
                data = int.from_bytes(data_bytes , byteorder='big',signed=True)/2**(dict_converter["rbits"])
                value = data * dict_converter["gradient"]
                await port.write_value(value)
                print('data to server is')
                print(await port.get_value())
            time.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())