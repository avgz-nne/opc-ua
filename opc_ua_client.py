import asyncio
import logging

from asyncua import Client

_logger = logging.getLogger('asyncua')
async def client_reader(client, idx, nodeid):
        print(idx, nodeid)
        var = client.get_node("ns="+idx+"i="+nodeid)
        data = await var.read_value()
        print('byte data is')
        print(data)
        return data
async def client_writer(client, idx, nodeid, data):
        print(idx, nodeid)
        var = client.get_node("ns="+idx+"i="+nodeid)
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
    async with Client(url=url) as client:
        _logger.info("Root node is: %r", client.nodes.root)
        _logger.info("Objects node is: %r", client.nodes.objects)
        coretigo_url = 'opc.tcp://192.168.1.100:4840/'
        tigo_client = Client(url=coretigo_url)
        # Node objects have methods to read and write node attributes as well as browse or populate address space
        _logger.info("Children of root are: %r", await client.nodes.root.get_children())

        # setup our own namespace, not really necessary but should as spec
        uri = 'http://nne.unibio'
        idx = await client.get_namespace_index(uri)
        _logger.info("index of our namespace is %s", idx)
        # get a specific node knowing its node id
       
        var1 = client.get_node("ns=2;i=2")
        tigo_nsidx = 6
        nsidx = 2
        tigo_nodeids = [32824, 98360, 163896, 1234] #[pressure pipe, #pressure tan level, temperature pipe, conductivity]
        nodeids = [2,3,4,5] #[pressure pipe, #pressure tan level, temperature pipe, conductivity]
        dict_conv1 = {"nbytes":4, "rbytes":4, "start":2 , "end":16, "gradient":0.01, "conversion": 1}
        dict_conv2 = {"nbytes":4, "rbytes":4, "start":2 , "end":16, "gradient":0.01, "conversion": 0.0254}
        dict_conv3 = {"nbytes":2, "rbytes":2, "start":0 , "end":16, "gradient":0.1, "conversion": 1}
        dict_conv4 = {"nbytes":2, "rbytes":2, "start":0 , "end":16, "gradient":0.1, "conversion": 1}
        converters = [dict_conv1 , dict_conv2, dict_conv3, dict_conv4]
        while(True):
            for tigo_nodeid, nodeid, converter in zip(tigo_nodeids, nodeids, converters):
                raw_data = client_reader(tigo_client, tigo_nsidx, tigo_nodeid)
                data = data_converter(raw_data, converter)
                client_writer.write_value(tigo_client,tigo_nsidx, tigo_nodeid, data)
            await asyncio.sleep(1)
       


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())