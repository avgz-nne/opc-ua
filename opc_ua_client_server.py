import asyncio
import logging
import time

from asyncua import Client, Server
from asyncua import ua

_logger = logging.getLogger('asyncua')

def client_reader(client, idx, node_id):
        var = client.get_node(ua.NodeId(1002, 2))
        data = var.read_value()
        print('byte data is '+ data)
        return data
def data_converter(bytes_raw, dict_converter):
        data_bytes = bytes_raw[dict_converter.start,dict_converter.end]
        data = int.from_bytes(data_bytes, byteorder='big',signed=True)
        value = data * dict_converter.gradient
        print('byte data is '+ data)
        return data

async def main():
    _logger = logging.getLogger('asyncua')
    # setup our server
    server = Server()
    await server.init()
    server.set_endpoint('opc.tcp://0.0.0.0:4840/nne_unibio/server/')
     # setup our own namespace, not really necessary but should as spec
    uri = 'http://nne.unibio'
    idx = await server.register_namespace(uri)
    # populating our address space
    # server.nodes, contains links to very common nodes like objects and root
    
    coretigo_url = 'opc.tcp://192.168.1.100:4840/'
    namespace_id = 3
    port1_nodeid = 2002
    port2_nodeid = 1234 # read from ua expert
    port3_nodeid = 2345 # read from ua expert
    port4_nodeid = 3456 # read from ua expert
    sensor1_conversion = 0
    client = Client(url=coretigo_url)
    async with server and client:
        myobj = await server.nodes.objects.add_object(idx, 'MyObject')
        port1_PI = await myobj.add_variable(idx, 'Port 1', 0.0)
        while True:
            var = client.get_node("ns=6;i=32824")
            print("My variable", var, await var.read_value())
            _logger.info('Set value of %s to %.1f', port1_PI, new_val)
            
            await myvar.write_value(new_val)

            uri = "http://examples.freeopcua.github.io"
            idx = await client.get_namespace_index(uri)
            _logger.info("index of our namespace is %s", idx)
            # get a specific node knowing its node id
            var = client.get_node(ua.NodeId(1002, 2))
            var = client.get_node("ns=3;i=2002")
            print(var)
            await var.read_data_value() # get value of node as a DataValue object
            #await var.read_value() # get value of node as a python builtin
            for i in range(100):
                var = client.get_node("ns=6;i=32824")
                print("My variable", var, await var.read_value())
                #print("My variable", var, await var.read_data_value())
                time.sleep(0.5)
       


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())