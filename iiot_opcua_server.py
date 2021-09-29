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
    # setup our server
    server = Server()
    await server.init()
    server.set_endpoint('opc.tcp://127.0.0.1:4840/nne_unibio/server/')
     # setup our own namespace, not really necessary but should as spec
    uri = 'http://nne.unibio'
    idx = await server.register_namespace(uri)
    server.allow_remote_admin(True)
    # populating our address space
    # server.nodes, contains links to very common nodes like objects and root
    async with server:
        myobj = await server.nodes.objects.add_object(idx, 'CIP_DATA')
        port1_PI = await myobj.add_variable(idx, 'Port 1', 0.0)
        port2_PI = await myobj.add_variable(idx, 'Port 2', 0.0)
        port3_PI = await myobj.add_variable(idx, 'Port 3', 0.0)
        port4_PI = await myobj.add_variable(idx, 'Port 4', 0.0)
        port1_PI.set_writable()
        port2_PI.set_writable()
        port3_PI.set_writable()
        port4_PI.set_writable()
        await server.export_xml([server.nodes.objects, server.nodes.root, myobj], "basic_opcua_cip.xml")
        while True:
            await asyncio.sleep(1)
            


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    asyncio.run(main(), debug=True)