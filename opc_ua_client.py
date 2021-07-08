import asyncio
import logging

from asyncua import Client

_logger = logging.getLogger('asyncua')

async def main():
    url = "opc.tcp://localhost:4840/freeopcua/server/"
    async with Client(url=url) as client:
        _logger.info("Root node is: %r", client.nodes.root)
        _logger.info("Objects node is: %r", client.nodes.objects)

        # Node objects have methods to read and write node attributes as well as browse or populate address space
        _logger.info("Children of root are: %r", await client.nodes.root.get_children())

        uri = "http://examples.freeopcua.github.io"
        idx = await client.get_namespace_index(uri)
        _logger.info("index of our namespace is %s", idx)
        # get a specific node knowing its node id
        var = client.get_node(ua.NodeId(1002, 2))
        var = client.get_node("ns=3;i=2002")
        print(var)
        await var.read_data_value() # get value of node as a DataValue object
        #await var.read_value() # get value of node as a python builtin
       


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())