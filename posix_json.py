import json




data_array = [{"version":"2.0","tagId":"200001449","timestamp":1631049569.3129342,"data":{"metrics":{"latency":49,"rates":{"success":0.97,"update":0.99,"packetLoss":0}},"tagData":{"blinkIndex":4563,"accelerometer":[[15,62,886],[-3,35,957],[7,42,941],[7,35,953],[0,35,949],[3,35,937],[7,46,933],[7,42,933],[11,39,933],[0,31,933],[11,42,929],[0,46,945],[7,31,937]]},"anchorData":[{"tagId":"200001449","anchorId":"11143","rss":-80.36},{"tagId":"200001449","anchorId":"57123","rss":-80.69},{"tagId":"200001449","anchorId":"20429","rss":-80.16},{"tagId":"200001449","anchorId":"6163","rss":-80.72}],"coordinates":{"x":870,"y":1092,"z":1000},"score":0.23405579678991342,"type":1,"zones":[]},"tagType":"2.0","success":True}]

print(data_array[0]["data"]["coordinates"]["x"])