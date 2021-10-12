import asyncio
import logging

from asyncua import Client, client

_logger = logging.getLogger('asyncua')
async def client_reader(client, idx, nodeid):
        node_string = "ns={};i={}".format(idx, nodeid)
        try: 
                var = client.get_node(node_string)
                data = await var.read_value()
        except:
                data = -1.0
        return data
async def client_writer(client, idx, nodeid, data):
        node_string = "ns={};i={}".format(idx, nodeid)
        var = client.get_node(node_string)
        #data = float(data)
        await var.write_value(data)
        return data
def data_converter(bytes_raw, dict_converter):
        print(bytes_raw)
        data_bytes = bytes_raw[dict_converter["start"]:dict_converter["end"]]
        data = int.from_bytes(data_bytes, byteorder='big',signed=True)/2**(dict_converter["rbytes"])
        print(data_bytes)
        print(data)
        value = data * dict_converter["gradient"]
        print(value)
        return value

async def main():
    url = "opc.tcp://admin@192.168.0.119:4840/nne_unibio/server/"
    #_logger.info("Root node is: %r", client.nodes.root)
    #_logger.info("Objects node is: %r", client.nodes.objects)
    coretigo_url = "opc.tcp://192.168.1.100:4840/"
  
    # Node objects have methods to read and write node attributes as well as browse or populate address space
    
    #_logger.info("Children of root are: %r", await client.nodes.root.get_children())

    # setup our own namespace, not really necessary but should as spec
    uri = 'http://nne.unibio'
    #_logger.info("index of our namespace is %s", idx)
    # get a specific node knowing its node id
    
    tigo_nsidx = 6
    nsidx = 2
    tigo_nodeids = [32824, 98360, 163896,229432] #[pressure pipe, #pressure tan level, temperature pipe, conductivity]
    nodeids = [2,3,4,5] #[pressure pipe, #pressure tan level, temperature pipe, conductivity]
    dict_conv1 = {"nbytes":4, "rbytes":4, "start":0 , "end":2, "gradient":0.01, "conversion": 1}
    dict_conv2 = {"nbytes":4, "rbytes":0, "start":0 , "end":2, "gradient":0.01, "conversion": 0.0254}
    dict_conv3 = {"nbytes":2, "rbytes":0, "start":0 , "end":2, "gradient":0.1, "conversion": 1}
    dict_conv4 = {"nbytes":2, "rbytes":0, "start":0 , "end":4, "gradient":1, "conversion": 1}
    converters = [dict_conv1 , dict_conv2, dict_conv3, dict_conv4]
    
    while(True):
            data_list = []
            async with Client(url=coretigo_url) as tigo_client:
                for tigo_nodeid, converter in zip(tigo_nodeids, converters):
                    raw_data = await client_reader(tigo_client, tigo_nsidx, tigo_nodeid)
                    data = data_converter(raw_data , converter)
                    data_list.append(data)
            print(data_list)
            async with Client(url=url) as client:
                for tigo_nodeid, nodeid, converter, data in zip(tigo_nodeids, nodeids, converters, data_list):
                    await client_writer(client, nsidx, nodeid, data)
            await asyncio.sleep(1)
       


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())