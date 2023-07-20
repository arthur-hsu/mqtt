import paho.mqtt.client as mqtt
import json, base64, codecs
#from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import time
import config.config as cf
from . import colorLog as log
import re, ast
import threading


class MQTT_Module:
    def __init__(self, hostIP, appID='', devEUI='', sub_topic='', pub_topic='', client_id='', client_pw='', port=1883):
        self.hostIP = hostIP
        if sub_topic == '':
            self.sub_topic = "application/%s/device/%s/event/up" % (str(appID), devEUI.lower())
            #application/fe42cb9f-e720-4383-8168-3e515a0b44c8/devices/6bb38dd1b5f62ae9/events
            #self.sub_topic = "application/%s/device/%s/rx" % (str(appID), devEUI.lower())
        else:
            self.sub_topic = sub_topic
        if pub_topic == '':
            self.pub_topic = "application/%s/device/%s/tx" % (str(appID), devEUI.lower())
        else:
            self.pub_topic = pub_topic
        self.client_id = client_id
        self.client_pw = client_pw
        self.grep_key = ["fPort", "data", "frequency", "dr"]
        self.dump = 1
        self.port = port
        self.tmplist=[]
    def getdata(self):
        if len(self.tmplist)!=0: 
            data=self.tmplist[0]
            self.tmplist.clear()
            return data
        
    def subscribe(self, loop_forever=0, timeout=30):
        if loop_forever==1:
            timeout= 'forever'
        log.Logger('Subscribe %s "%s" for %s sec' %(self.hostIP, self.sub_topic, timeout), 'BLACK', 'WHITE', 0)
        self.recv_list = []
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        for i in range(3):
            try:
                if self.client_id != '':
                    client.username_pw_set(self.client_id, self.client_pw)
                client.connect(self.hostIP, self.port)
            except Exception as e:
                time.sleep(1)
                if i ==2 :
                    log.Logger(str(e))
                    log.Logger('Failed to connect to MQTT Broker...', fore='RED')
                    return False
        if loop_forever == 0:
            client.loop_start()
            #time_start = time.time()
            #while time.time() < (time_start + timeout):
            #    client.loop()
            time.sleep(timeout)
            client.loop_stop()
            client.disconnect()
            log.Logger('MQTT subscriber: End')
        else:
            self.dump=0
            client.loop_forever()
        return self.recv_list
    
    def publish(self, confirmed, fPort, data):
        b64 = codecs.encode(codecs.decode(data, 'hex'), 'base64').decode().rstrip('\n')
        send = json.dumps({"confirmed": confirmed, "fPort": int(fPort), "data": b64})

        client = mqtt.Client()
        for i in range(3):
            try:
                if self.client_id != '':
                    client.username_pw_set(self.client_id, self.client_pw)
                client.connect(self.hostIP, self.port)
            except Exception as e:
                time.sleep(1)
                if i ==2 :
                    log.Logger('%s, \nFailed to connect to MQTT Broker...' %str(e))
                    return False

        log.Logger("Publish to %s : {\"confirmed\": %s, \"fPort\": %s, \"data\": %s}" %(self.hostIP, confirmed, fPort,data), 'BLACK', 'WHITE', timestamp=0)
        client.publish(self.pub_topic, send)
        client.disconnect()



    def on_connect(self, client, userdata, flags, rc):
        #log.Logger("Connected with result code "+str(rc))
        client.subscribe(self.sub_topic)


    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode("utf-8", 'ignore'))
            data['data'] = base64.b64decode(data['data'].encode("utf-8")).hex()
        except:
            data = msg.payload.decode('utf-8')
        #data = data.items()
        #data = pd.DataFrame(list(data),columns=['key', 'value']).set_index("key")
        #log.Logger(data)
        new_data = {}
        if 'applicationID' in data:
            rx_dic = data['rxInfo'][0]
            tx_dic = data['txInfo']
            data = {**data, **tx_dic, **rx_dic}
            handle = ['timestamp', 'fCnt', 'rssi', 'loRaSNR', 'frequency', 'dr', 'fPort', 'data'] 
            #handle = ['fCnt', 'rssi','dr', 'fPort', 'data' ] 
            for i in handle:
                if i in data.keys():
                    if i == 'frequency':
                        new_data['freq'] = data[i]
                    else:
                        new_data[i] = data[i]
        elif not type(data) == type({}):
            new_data['data'] = data
        else:
            new_data = data

        if 'timestamp' not in new_data:
            new_data['timestamp'] = int(time.time())


        value=''
        remove_sn_data = new_data['data'][10:] if '7e' in new_data['data'] else new_data['data']
        unit_dict = {'T': [0.1, '°C', "\d\w67([^?]\w\w\w)", '67'], \
                     'H': [1, '%', "\d\w68([^?]\w)", '68'], \
                     'Hi': [0.1, '%', "\d\w70([^?]\w\w\w)", '70'], \
                     'P': [0.1, 'hPA', "\d\w73([^?]\w\w\w)", '73'], \
                     'A': [0.001, 'G', "\d\w71([^?]\w\w\w\w\w\w\w\w\w\w\w)", '71'], \
                     'pH': [0.1, '', "\d\wc2([^?]\w\w\w)", 'c2'], \
                     'WS': [0.01, 'm/s', "\d\wbe([^?]\w\w\w)", 'be'], \
                     'WD': [1, '°', "\d\wbf([^?]\w\w\w)", 'bf'], \
                     #'DI': [1, '', "\d\w00([^?]\w)", '00'], \
                     #'DO': [1, '', "\d\w01([^?]\w)", '01'], \
                     'Pyranometer': [1, 'W/m2', "\d\wc3([^?]\w\w\w)", 'c3'], \
                     'EC': [0.001, 'mS/cm', "\d\wc0([^?]\w\w\w)", 'c0']}
                     #'AIC': [0.01, 'mA', "\d\w02([^?]\w\w\w)", '02']
        for sensor_type in unit_dict.keys():
            _value = re.findall(unit_dict[sensor_type][2],remove_sn_data)
            if len(_value)>0:
                for i in _value:
                    #remove_sn_data = remove_sn_data.replace(i,'')
                    unit = unit_dict[sensor_type]
                    if sensor_type == 'A':
                        value += 'XYZ: %s%s, %s%s, %s%s, '   %(round(twosComplement_hex(i[0:4])*unit[0],2), unit[1],\
                                                               round(twosComplement_hex(i[4:8])*unit[0],2), unit[1],\
                                                               round(twosComplement_hex(i[8:12])*unit[0],2), unit[1])
                    else:
                        value += '%s: %s%s, '   %(sensor_type, round(twosComplement_hex(i)*unit[0],2), unit[1])
                    remove_sn_data = re.sub('\d\w%s%s'%(unit_dict[sensor_type][-1], i), '', remove_sn_data)

        if len(value) > 0 :
            value = '\n%s%s'%(' '*110, value[0:-2])

        if self.dump == 1:
            self.recv_list.append(new_data)
        self.tmplist.append(new_data)
        #log.Logger('\n  %s %s' %(new_data, value))
        #print(json.dumps(data, sort_keys=True, indent=4, separators=(', ', ': ')))






def twosComplement_hex(hexval):
    bits = 16
    val = int(hexval, bits)
    if val & (1 << (bits-1)):
        val -= 1 << bits
    return val







'''
import mqtt_lib as matt
matt = matt.MQTT_Module('169.254.26.109', '1', '0102030405066666')
result = matt.subscribe()
matt.publish('False', 1, '1abcddeadabcddead1')
'''
