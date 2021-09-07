import asyncio
import logging

from asyncua import Client, client

_logger = logging.getLogger('asyncua')
async def client_reader(client, idx, nodeid):
        print(idx, nodeid)
        node_string = "ns={};i={}".format(idx, nodeid)
        var = client.get_node(node_string)
        print(node_string)
        data = await var.read_value()
        print('byte data is')
        print(data)
        return data
async def client_writer(client, idx, nodeid, data):
        print(idx, nodeid)
        node_string = "ns={};i={}".format(idx, nodeid)
        var = client.get_node(node_string)
        data = await var.write_value(data)
        print('byte data is')
        print(data)
        return data
def data_converter(bytes_raw, dict_converter):
        data_bytes = bytes_raw[dict_converter["start"],dict_converter["end"]]
        data = int.from_bytes(data_bytes, byteorder='big',signed=True)
        value = data * dict_converter["gradient"]
        return value

async def main():
    url = "opc.tcp://admin@127.0.0.1:4840/nne_unibio/server/"
    client = Client(url=url)
    await client.connect()
    #_logger.info("Root node is: %r", client.nodes.root)
    #_logger.info("Objects node is: %r", client.nodes.objects)
    coretigo_url = "opc.tcp://admin@127.0.0.2:4840/nne_unibio/server/"
    tigo_client = Client(url=coretigo_url)
    await tigo_client.connect()
    # Node objects have methods to read and write node attributes as well as browse or populate address space
    
    #_logger.info("Children of root are: %r", await client.nodes.root.get_children())

    # setup our own namespace, not really necessary but should as spec
    uri = 'http://nne.unibio'
    idx = await client.get_namespace_index(uri)
    #_logger.info("index of our namespace is %s", idx)
    # get a specific node knowing its node id
    
    var1 = client.get_node("ns=2;i=2")
    tigo_nsidx = 2
    nsidx = 2
    tigo_nodeids = [2,3,4,5] #[pressure pipe, #pressure tan level, temperature pipe, conductivity]
    nodeids = [2,3,4,5] #[pressure pipe, #pressure tan level, temperature pipe, conductivity]
    dict_conv1 = {"nbytes":4, "rbytes":4, "start":2 , "end":16, "gradient":0.01, "conversion": 1}
    dict_conv2 = {"nbytes":4, "rbytes":4, "start":2 , "end":16, "gradient":0.01, "conversion": 0.0254}
    dict_conv3 = {"nbytes":2, "rbytes":2, "start":0 , "end":16, "gradient":0.1, "conversion": 1}
    dict_conv4 = {"nbytes":2, "rbytes":2, "start":0 , "end":16, "gradient":0.1, "conversion": 1}
    converters = [dict_conv1 , dict_conv2, dict_conv3, dict_conv4]
    while(True):
        for tigo_nodeid, nodeid, converter in zip(tigo_nodeids, nodeids, converters):
            raw_data = await client_reader(tigo_client, tigo_nsidx, tigo_nodeid)
            print
            await client_writer.write_value(client, tigo_nsidx, tigo_nodeid, raw_data)
        await asyncio.sleep(1)
       


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())