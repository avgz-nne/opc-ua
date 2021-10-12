from enum import Flag
import paho.mqtt.client as mqtt
import time
import sys
import asyncio
import logging
import json

from asyncua import Client, client

def on_message(posix_client, userdata, message):
        data_array = message[0]["data"]
        coordinates = data_array["coordinates"]
        xpos = coordinates["x"]
        ypos = coordinates["y"]
        zpos = coordinates["z"]
        zones = data_array['zones']
        data_list = [xpos, ypos]
        print(message.payload.decode())
        print(xpos)
        client_writer(data_list)

def on_connect(posix_client, userdata, message):
        global connected_flag
        connected_flag = True
        return connected_flag
        
def on_disconnect(posix_client, userdata, message):
        global connected_flag
        connected_flag = False
        return connected_flag
##[{"version":"2.0","tagId":"200001449","timestamp":1631049569.3129342,"data":{"metrics":{"latency":49,"rates":{"success":0.97,"update":0.99,"packetLoss":0}},"tagData":{"blinkIndex":4563,"accelerometer":[[15,62,886],[-3,35,957],[7,42,941],[7,35,953],[0,35,949],[3,35,937],[7,46,933],[7,42,933],[11,39,933],[0,31,933],[11,42,929],[0,46,945],[7,31,937]]},"anchorData":[{"tagId":"200001449","anchorId":"11143","rss":-80.36},{"tagId":"200001449","anchorId":"57123","rss":-80.69},{"tagId":"200001449","anchorId":"20429","rss":-80.16},{"tagId":"200001449","anchorId":"6163","rss":-80.72}],"coordinates":{"x":870,"y":1092,"z":1000},"score":0.23405579678991342,"type":1,"zones":[]},"tagType":"2.0","success":true}]
##[{,"tagId":"200001449","data":{"coordinates":{"x":870,"y":1092,"z":1000},"score":0.23405579678991342,"type":1,"zones":[]},"tagType":"2.0","success":true}]

_logger = logging.getLogger('asyncua')
async def client_writer(data_list):
        url = "opc.tcp://admin@192.168.0.119:4840/nne_unibio/server/"
        nodeids = [6,7,8]
        idx=2
        
        async with Client(url=url) as client:
                for  nodeid, data in zip(nodeids, data_list):
                        node_string = "ns={};i={}".format(idx, nodeid)
                        var = client.get_node(node_string)
                        data = float(data)
                        await var.write_value(data)
        return True

async def main():
        HOST = '192.168.0.103'
        PORT = 1883
        TOPIC = 'tags'
        DURATION = 3
        client = mqtt.Client()  # create new instance
        connected_flag = False
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        while True:
                if connected_flag  == False:
                        try:
                                client.connect(HOST, port=PORT)  # connect to host
                                client.on_message = on_message  # attach function to callback
                                client.loop_start()  # start the loop
                                client.subscribe(TOPIC)  # subscribe to topic
                        except Exception as E:
                                print(E)
                time.sleep(DURATION)  # wait for duration seconds
        #client.disconnect()


       


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())