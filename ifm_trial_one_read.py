import  xml.etree.ElementTree as ET
import requests
import json
import time
import re
import boto3
from botocore.exceptions import ClientError
import os
from datetime import datetime
# IP FOR MASTER
url = 'http://169.254.189.227/'

# STATIC HEADER
headers = {
  'Content-Type': 'text/plain'
}

i = 1
read_blob_data_payload = "{\"code\": \"request\", \"cid\": 1235, \"adr\": \"/iolinkmaster/port["+str(i)+"]/iolinkdevice/pdin/getdata\"}"

s3 = boto3.resource('s3')

def create_parser_dictionaries(filepath):
    unit_codes_SI = [
    1000, # K degrees
    1001, # C degrees
    1010, # meters
    1023, #m2
    1034, #m3
    1054, #s
    1061, #m/s
    1076, #m2/s
    ]
    string_unit_codes_SI = [
        '1000', # K degrees
        '1001', # C degrees
        '1010', # meters
        '1023', #m2
        '1034', #m3
        '1054', #s
        '1061', #m/s
        '1076', #m/s2
    ]
    dict_unit_codes_SI = {
        '1000': 'K degrees',
        '1001': 'C degrees',
        '1010': 'meters',
        '1023': 'm2',
        '1034': 'm3',
        '1054': 's',
        '1061': 'm/s',
        '1076': 'm/s2',
    }
    tree = ET.parse(filepath)
    root = tree.getroot()

    level_0 = root.findall('./{http://www.io-link.com/IODD/2010/10}ProfileBody')
    level_0_1 = level_0[0]
    level_1 = level_0_1.findall('./{http://www.io-link.com/IODD/2010/10}DeviceFunction')
    level_1_1 = level_1[0]
    level_2 = level_1_1.findall('./{http://www.io-link.com/IODD/2010/10}ProcessDataCollection')
    level_2_1 = level_2[0]
    level_3 = level_2_1.findall('./{http://www.io-link.com/IODD/2010/10}ProcessData')
    level_3_1 = level_3[0]
    level_4 = level_3_1.findall('./{http://www.io-link.com/IODD/2010/10}ProcessDataIn')
    level_4_1 = level_4[0]
    level_5 = level_4_1.findall('./{http://www.io-link.com/IODD/2010/10}Datatype')
    records_collection = level_5[0]

    level_2 = level_1_1.findall('./{http://www.io-link.com/IODD/2010/10}UserInterface')
    level_2_1 = level_2[0]
    level_3 = level_2_1.findall('./{http://www.io-link.com/IODD/2010/10}MenuCollection')
    level_3_1 = level_3[0]
    menus = level_3_1.findall('./{http://www.io-link.com/IODD/2010/10}Menu')

    text_root =  root.findall('./{http://www.io-link.com/IODD/2010/10}ExternalTextCollection')
    text_root_1 = text_root[0]
    text_1 = text_root_1.findall('./{http://www.io-link.com/IODD/2010/10}PrimaryLanguage')
    text_1_1 = text_1[0]

    data_parse_dictionary = []
    i = 0
    total_length = records_collection.get('bitLength')
    for record in records_collection:
        data_parse_dictionary.append({}) 
        data = record.findall('./{http://www.io-link.com/IODD/2010/10}SimpleDatatype')
        names = record.findall('./{http://www.io-link.com/IODD/2010/10}Name')
        nameid = names[0].get('textId')
        text = text_1_1.findall("./{http://www.io-link.com/IODD/2010/10}Text[@id='"+ nameid +"']")
        data_parse_dictionary[i]['name'] = text[0].get('value')
        data_parse_dictionary[i]['bitOffset'] = record.get('bitOffset')
        data_parse_dictionary[i]['subindex'] = record.get('subindex')
        data_parse_dictionary[i]['bitLength'] = data[0].get('bitLength')
        valueRange = data[0].findall('./{http://www.io-link.com/IODD/2010/10}ValueRange')
        if len(valueRange):
            data_parse_dictionary[i]['low_val'] = valueRange[0].get('lowerValue')
            data_parse_dictionary[i]['up_val'] = valueRange[0].get('upperValue')
        i = i + 1 

    for menu in menus:
        for unit in string_unit_codes_SI:
            if re.search("^M_MR_SR_Observation_.*"+unit+"$", menu.get("id")):
                records = menu.findall('./{http://www.io-link.com/IODD/2010/10}RecordItemRef')
                record= records[0]
                subindex = record.get("subindex")
                for data_parse_dic in data_parse_dictionary:
                    if data_parse_dic['subindex'] == subindex:
                        data_parse_dic['gradient'] = record.get("gradient")
                        data_parse_dic['offset'] = record.get("offset")
                        data_parse_dic['displayFormat'] = record.get("displayFormat")
                        data_parse_dic['unitCode'] = record.get("unitCode")
                        data_parse_dic['units'] = dict_unit_codes_SI[record.get("unitCode")]
  

    # Payloads:
    #   Start and stop recording

    

    return data_parse_dictionary, total_length

def data_parser(data_parse_dictionary, total_length, hex_value):
    data_dictionary = {}
    for data_point in data_parse_dictionary:
        if ('up_val' in data_point):
            hex_start = int((int(total_length) - int(data_point['bitOffset']) - int(data_point['bitLength'])) / 4)
            hex_end = int((int(total_length) - int(data_point['bitOffset'])) / 4)
            total_bits = int(data_point['bitLength'])
            low_val = int(data_point['low_val'])
            up_val = int(data_point['up_val'])
            if ('offset' in data_point):
                offset = int(data_point['offset'])
            else:
                offset = 0
            data_point['value'] = int(hex_value[hex_start:hex_end], 16) * (up_val - low_val) / (2**(total_bits-1)) + offset
    
    data_dictionary['values'] = data_parse_dictionary
    data_dictionary['timestamp'] = str(datetime.now())
    return data_dictionary

def upload_file(bucket_name, json_data):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """
    filename = 'vibration-poc' + str(datetime.now()) +'.json'
    s3object = s3.Object(bucket_name, filename)

    s3object.put(
        Body=(bytes(json.dumps(json_data).encode('UTF-8')))
    )

data_parse_dictionary, total_length = create_parser_dictionaries("ifm-vvb020.xml")
j = 0

while  j < 10000:
    response = requests.request("POST", url, headers=headers, data=read_blob_data_payload)
    json_data = json.loads(response.text)  # convert to json
    return_code = json_data["code"]
    if return_code != 200:
        print("Error in transmission, code: ", return_code)
        exit(0)
    value = json_data['data']['value']
    parsed_data_dic = data_parser(data_parse_dictionary, total_length, value)
    upload_file('iot-test-lundbeck-poc-ifm', parsed_data_dic)
    j = j + 1
    time.sleep(10)
