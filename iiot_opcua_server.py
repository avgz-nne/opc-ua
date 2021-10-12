import logging
import asyncio
import sys
sys.path.insert(0, "..")

from asyncua import ua, Server
from asyncua.common.methods import uamethod



@uamethod
def func(parent, value):
    return value * 2


async def main():
    _logger = logging.getLogger('asyncua')
    # setup our server
    nsidx = 6
    nodeids = [32824, 98360, 163896] #[pressure pipe, #pressure tan level, temperature pipe]
    dict_conv1 = {"nbytes":4, "rbits":4, "start":0 , "end":2, "gradient":0.01, "conversion": 1}
    dict_conv2 = {"nbytes":4, "rbits":0, "start":0 , "end":2, "gradient":0.01, "conversion": 0.0254}
    dict_conv3 = {"nbytes":2, "rbits":0, "start":0 , "end":2, "gradient":0.1, "conversion": 1}
    converters = [dict_conv1 , dict_conv2, dict_conv3]
    # setup our server
    server = Server()
    await server.init()
    server.set_endpoint('opc.tcp://192.168.0.119:4840/nne_unibio/server/')
     # setup our own namespace, not really necessary but should as spec
    uri = 'http://nne.unibio'
    idx = await server.register_namespace(uri)
    server.allow_remote_admin(True)
    # populating our address space
    # server.nodes, contains links to very common nodes like objects and root
    async with server:
        myobj = await server.nodes.objects.add_object(idx, 'CIP_DATA')
        port1_PI = await myobj.add_variable(idx, 'CIP_Pressure', 0.0)
        port2_PI = await myobj.add_variable(idx, 'CIP_tank_level', 0.0)
        port3_PI = await myobj.add_variable(idx, 'CIP_temperature', 0.0)
        port4_PI = await myobj.add_variable(idx, 'CIP_conductivity', 0.0)
        await server.export_xml([server.nodes.objects, server.nodes.root, myobj], "basic_opcua_cip.xml")
        while True:
            await asyncio.sleep(1)
            


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    asyncio.run(main(), debug=True)