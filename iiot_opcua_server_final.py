import logging
import asyncio
import sys
sys.path.insert(0, "..")

from asyncua import ua, Server



async def main():
    _logger = logging.getLogger('asyncua')
    # setup our server
    # setup our server
    server = Server()
    await server.init()
    server.set_endpoint('opc.tcp://192.168.0.119:4840/nne_unibio/server/') # new address here should be 192.168.10.10
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
        myobj2 = await server.nodes.objects.add_object(idx, 'CIP_DATA')
        port5_PI = await myobj2.add_variable(idx, 'X_position', 0.0)
        port6_PI = await myobj2.add_variable(idx, 'Y_position', 0.0)
        port7_PI = await myobj2.add_variable(idx, 'Zone', 'Container 0')
        await server.export_xml([server.nodes.objects, server.nodes.root, myobj], "basic_opcua_cip.xml")
        while True:
            await asyncio.sleep(1)
            


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    asyncio.run(main(), debug=True)