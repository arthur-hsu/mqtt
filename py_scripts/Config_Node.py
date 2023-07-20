import src.colorLog as log
import src.mqtt_lib as mqtt_lib
import src.commonFunction as commonFunction
from py_scripts import String_Handling
import src.serial_lib as serial_lib
import allure
import time, os, re, json, zlib
import pandas as pd


pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.max_colwidth', 100)
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)

fun = commonFunction.Common()


@allure.step("Subscribe and Collect data over MQTT")
def MQTT_Subscribe(remote_ip, app_index, DevEUI, intv, sub_topic='', pub_topic=''):
    print('start MQTT_Subscribe')
    mqtt = mqtt_lib.MQTT_Module(remote_ip, appID=app_index, devEUI= DevEUI, sub_topic=sub_topic, pub_topic=pub_topic, client_id='username', client_pw='password')
    mesg = mqtt.subscribe(0, int(intv))
    #print(f'{mesg=}')#debug
    return mesg

def nb_application(serial, app):
    with open('topo/nb_application.json', 'r') as f:
        nb_application = json.load(f)
    serial.set_timeout(5)
    for i in nb_application[app]:
        if type(i) == type([]):
            serial.write(i[0], i[1])
        else:
            serial.write(i,'OK')
    serial.write('atc+dataencap=0', 'OK')
    serial.set_timeout(15)
    result = serial.write('ATC+NBIOT_APPLY=1', '+EVT:NB_CONNECT')
    serial.set_timeout(3)
    return True if result else False





def MQTT_Parser(data, ssn, snsr_id_type, expected_intv=60):
    log.Logger('*** Verify the interval of type %s on Probe %s should be %s' %(snsr_id_type, ssn, expected_intv), 'BLACK', 'WHITE', 0)
    handle = []
    result = 0
    if data == False:
        return result
    for i in data:
        if '7e' not in i['data'] :
            ssn = ''
        if all(string in i['data'] for string in [ssn, snsr_id_type]):
            log.Logger(str(i), timestamp=0)
            handle.append(int(i['timestamp']))
            if len(handle) >= 2:
                break
    log.Logger('\tCalculation Time Interval : %s' %str(handle), fore='GREEN', timestamp=0)
    if len(handle) > 1 :
        interval = (handle[-1] - handle[-2]) 
        if abs(int(expected_intv) - interval) <= (int(expected_intv)/7):
            result += 1
    else:
        interval = 'None'
    log.Logger('\tInterval : %s' %str(interval), timestamp=0)
    return result


def grep_prb_ssn(serial, port):
    while True:
        dump = serial.write('ATC+PRB_INFO=%s?'%port, expected='OK', dump_duration=5)
        ret = re.findall('PRB_INFO=([^?].*):([^?].*):([^?].*):([^?].*):([^?].*):([^?].*)', dump)
        if ret:
            return ret[0][-2][0:-1] + '0' + ret[0][-2][-1]

def grep_snsr_id_type(configuration_dict, snsr_index=''):
    log.Logger("*** Grep sensor's type", 'BLACK', 'WHITE', 0)
    #log.Logger('\n%s' %str(configuration_dict))
    snsr_id_type_list = []
    for i in range(1, len(configuration_dict.keys())):
        sensor_key = list(configuration_dict.keys())[i]
        snsr_id = int(sensor_key.split(':')[-1])
        hex_string = hex(snsr_id).replace('0x','')
        length = 2
        if len(hex_string)<length:
            hex_string = '0'*(length-len(hex_string))+hex_string
        snsr_id = hex_string
        sensor_info = configuration_dict[sensor_key]['INFO']
        if not any(info in sensor_info for info in ['f1', 'f2', 'f3']):
            snsr_id_type_list.append(snsr_id.zfill(2)+sensor_info)
    log.Logger(str(snsr_id_type_list), timestamp=0)
    if snsr_index != '': 
        return snsr_id_type_list[snsr_index]
    else:
        return snsr_id_type_list


@allure.step("Join_LoRA_Network")
def Join_LoRA_Network(serial, NJM, cls, appkey, DevEUI, BAND, MASK='0000', ADR=1, DR=0, CFM=1):
    log.Logger("*** Join_LoRA_Network", 'BLACK', 'WHITE', 0)
    serial.write('ATR', ['OK', 'RAK'], makeTrue=2)
    time.sleep(2)
    serial.write('ATZ', '')
    time.sleep(3)
    serial.write('AT+NJM=%s' %NJM, '')
    serial.write('AT+CLASS=%s' %cls.upper(), 'OK', makeTrue=1)
    serial.write('AT+APPKEY=%s' %appkey, 'OK', makeTrue=1)
    serial.write('AT+DEVEUI=%s' %DevEUI, 'OK', makeTrue=1)
    serial.write('AT+BAND=%s' %BAND, 'OK', makeTrue=1)
    mask_only =  [1, 5, 6]
    if int(BAND) in mask_only:
        serial.write('AT+MASK=%s' %MASK, 'OK', makeTrue=1)
    serial.write('AT+CFM=%s' %CFM, 'OK', makeTrue=1)
    serial.write('AT+ADR=%s' %ADR, 'OK', makeTrue=1)
    if ADR == 0 :
        serial.write('AT+DR=%s' %DR, 'OK', makeTrue=1)
    serial.set_timeout(15)
    serial.write('AT+JOIN=1:1:8:10', '+EVT:JOINED')
    result = False
    for i in range(8):
        dump = serial.write('AT+NJS=?', 'OK', 0, 1)
        if 'AT+NJS=1' in dump:
            result = True
            break
        else:
            serial.write('AT+JOIN=1:1:8:10', '+EVT:JOINED')
    serial.set_timeout(3)
    time.sleep(2)
    serial.Close()
    return result


def grep_board_name(serial):
    #board_name = String_Handling.grep_return('AT+HWMODEL=?', serial).upper()
    dump = String_Handling.grep_return('AT+VER=?', serial)
    serial.Close()
    board_name_list = ['RAK4631', 'RAK3172','RAK3272-SiP', 'RAK3272LP-SiP', 'RAK11720', 'RAK5010']
    for board_name in board_name_list:
        if board_name in dump:
            return board_name



def grep_FQBN(serial):
    FQBN = fun.shell('arduino-cli board search %s'%grep_board_name(serial)).split(' ')[-3]
    serial.Close()
    return FQBN


def found_the_board_image(board_name, path):
    board_name_dic = {'RAK4631': 'dfu_package.zip',
                      'RAK5010': 'dfu_package.zip',
                      'RAK11720': 'RAK11720.bin'}
    files = os.listdir(path)
    for file in files:
        if board_name in file:
            path += '/%s'%file
            break
    if board_name in board_name_dic:
        _filter = board_name_dic[board_name]
    else:
        _filter = '.bin'
    files = os.listdir(path)
    for file in files:
        if _filter in file:
            path += '/%s'%file
            return path




def DFU_over_serial(port, FQBN, img_path):
    if os.path.isdir(img_path):
        img_path = '--input-dir %s'%img_path
    else:
        img_path = '--input-file %s'%img_path
    result = fun.shell('arduino-cli upload -p %s --fqbn %s %s 2>&1'%(port, FQBN, img_path), ['Upgrade Complete', 'Bootload completed successfully', 'Device programmed'])
    time.sleep(5)
    for i in range(600):
        time.sleep(0.1)
        if serial_lib.Port_is_alive(port):
            time.sleep(2)
            break
        elif i == 599:
            log.Logger('Failed to open %s' %port, fore='RED')
            return False
    return result 


def Get_BLE_MAC(serial):
    ble_mac = serial.write('ATC+BTMAC=?', expected='ATC+BTMAC=', makeTrue=1)
    if ble_mac:
        pattern = re.compile('.{2}')
        ble_mac = ble_mac.replace('ATC+BTMAC=','')
        ble_mac = ':'.join(pattern.findall(ble_mac))
    serial.Close()
    return ble_mac

def grep_snsr_id(prb_id, serial):
    data = serial.write('ATC+SNSR_CNT=%s?' %prb_id, 'ATC+SNSR_CNT=', makeTrue=1)
    snsr_id_list = []
    if not data:
        return snsr_id_list
    for i in data.split(':'):
        tmp = filter(str.isdigit, i)
        tmp = ''.join(list(tmp))
        snsr_id_list.append(tmp)
    snsr_id_list.pop(0)
    snsr_id_list.pop(0)
    log.Logger('\tsnsr_id_list = %s '%snsr_id_list, timestamp=0)
    return snsr_id_list


def Set_Configuration(serial, prb_id, prb_intv=60, snsr_index='all', snsr_intv=40, snsr_rule=8, snsr_hthr=300, snsr_lthr=100, Max_Probe=4):
    log.Logger("*** Set Probe_%s intv_%s, Sensor_%s intv_%s, snsr_rule_%s, snsr_hthr_%s, snsr_lthr_%s" %(prb_id, prb_intv, snsr_index, snsr_intv, snsr_rule, snsr_hthr, snsr_lthr), 'BLACK', 'WHITE', 0)
    prbid_snsrid_list = []
    serial.set_timeout(5)
    info = serial.write('ATC+PRB_INFO=%s?' %prb_id, 'PRB_INFO', makeTrue=1)
    if not info:
        return False
    if all(string in info for string in ['RAK2560-io', 'GE']) :
        serial.write('ATC+IO_CFG=%s:rs485:9600:8:1:0'%prb_id, 'OK', 2)
        remap = 0
        if remap == 1:
            serial.write('atc+io_psm=1:1:1:5000:1', 'OK', 2)
            commnd = [
                        ['010300000001', '6:1:190:RK900'], 
                        ['010300010001', '6:1:191:winddir'], 
                        ['010300020001', '4:1:103:Temperature'], 
                        ['010300030001', '6:1:112:humidity'],
                        ['010300040001', '6:1:115:Pressure']
                    ]
            '''commnd = [
                        ['010301f40001', '6:1:190:RK900'], 
                        ['010301f60001', '6:1:191:winddir'], 
                        ['010301f90001', '4:1:103:Temperature'], 
                        ['010301f80001', '6:1:112:humidity'],
                        ['010301f90001', '6:1:115:Pressure']
                    ]
            commnd = [
                        ['0103001E0001', '4:1:190:wind'],
                        ['0103001F0001', '4:1:191:winddir'],
                        ['010300200001', '4:1:103:Temperature']
                    ]'''
            for i in range(len(commnd)):
                serial.write('ATC+IO_ADDPOLL=%s:RS485:%s:%s:%s:3000:2:%s' %(prb_id, i+1, commnd[i][0], snsr_intv, commnd[i][1]), 'OK', makeTrue=1)
                time.sleep(0.5)
            serial.set_timeout(20)
            serial.write('atc+prb_del=%s'%prb_id, 'ADD', 1)
            time.sleep(5)

        else:
            commnd = ['010301f40001', '010301f60001', '010301f90001']
            #commnd = ['0103001E0001', '0103001F0001', '010300200001']
            for i in range(len(commnd)*(5-Max_Probe)-1):
                serial.write('ATC+IO_ADDPOLL=%s:RS485:%s:%s:%s:3000:2' %(prb_id, i+4, commnd[i%len(commnd)], snsr_intv), 'OK', makeTrue=1)
                time.sleep(1)

        serial.set_timeout(5)
    serial.write('ATC+PRB_INTV=%s:%s' %(prb_id, prb_intv), 'OK', makeTrue=1)
    snsr_id_list = grep_snsr_id(prb_id, serial)
    if not snsr_id_list:
        return False
    remove_cnt=0
    for i in range(len(snsr_id_list)):
        dump =  String_Handling.grep_return('ATC+SNSR_INFO=%s:%s?'%(prb_id, snsr_id_list[i-remove_cnt]), serial)
        if any(info in dump for info in ['f1', 'f2', 'f3']):
            snsr_id_list.pop(i-remove_cnt)
            remove_cnt+=1

    if snsr_index == 'all': 
        for i in range(len(snsr_id_list)):
            prbid_snsrid_list.append('%s:%s'  %(prb_id, snsr_id_list[i]))
    elif len(snsr_id_list) < int(snsr_index)+1:
        log.Logger('snsr_index is out of range.')
        return False
    else:
        prbid_snsrid_list.append('%s:%s'  %(prb_id, snsr_id_list[int(snsr_index)]))
    log.Logger('\tSensor List : %s' %prbid_snsrid_list, fore='GREEN', timestamp=0)
    cmd_list = ['INTV=$snsr_id:%s' %snsr_intv, 'RULE=$snsr_id:%s' %snsr_rule, 'HTHR=$snsr_id:%s' %snsr_hthr, 'LTHR=$snsr_id:%s' %snsr_lthr]
    for i in prbid_snsrid_list:  
        for cmd in cmd_list:
            serial.write('ATC+SNSR_%s' %(cmd.replace('$snsr_id', i)), 'OK', makeTrue=1)
        serial.set_timeout(3)
    serial.write('', '+EVT:UPD_SENSR: %s'%i)



def Get_Configuration(serial, prb_id):
    log.Logger("*** Get interval and rule on Probe_%s" %prb_id, 'BLACK', 'WHITE', 0)
    configuration_dict = {} 
    serial.set_timeout(3)
    info = serial.write('ATC+PRB_INFO=%s?' %prb_id, 'PRB_INFO', 1)
    data = serial.write('ATC+PRB_INTV=%s?' %prb_id, 'ATC+PRB_INTV', makeTrue=1)
    configuration_dict['%s_INTV' %prb_id] = re.findall('PRB_INTV=%s:([^?].*)'%prb_id, data)[0]

    snsr_id_list = grep_snsr_id(prb_id, serial)
    prbid_snsrid_list = []
    for i in range(len(snsr_id_list)):
        prbid_snsrid_list.append('%s:%s'  %(prb_id, snsr_id_list[i]))
    log.Logger('Prbid_Snsrid : %s' %prbid_snsrid_list, fore='GREEN', timestamp=0)

    for i in prbid_snsrid_list:
        inner_key = ['ATC+SNSR_INFO=%s' %i, 'ATC+SNSR_INTV=%s' %i, 'ATC+SNSR_RULE=%s' %i, 'ATC+SNSR_HTHR=%s' %i, 'ATC+SNSR_LTHR=%s' %i]
        inner_value = []
        for cmd in inner_key:
            data = serial.write(cmd+'?', cmd, makeTrue=1)
            inner_value.append(data.replace(cmd+':', ''))
        inner_key = ['INFO', 'INTV', 'RULE', 'HTHR', 'LTHR']
        inner_dict = dict(zip(inner_key, inner_value))
        configuration_dict[i] = inner_dict

    if all(string in info for string in ['RAK2560-io', 'GE']) :
        task_list = serial.write('ATC+IO_POLLCNT=%s:RS485?'%prb_id, 'ATC+IO_POLLCNT=', makeTrue=1).replace('OK','').split(':')
        for i in range(task_list.index('rs485')+2):
            task_list.pop(0)
        ipso = {'rs485': 'f1', 'sdi12': 'f2'}
        inner_key = ['INFO', 'CMD', 'INTV', 'Timeout', 'Retry']
        for task_id in task_list:
            task_info = serial.write('ATC+IO_POLLTASK=%s:rs485:%s?'%(prb_id, task_id), 'IO_POLLTASK', 1).replace('OK','').split(':')
            task_info.pop(0)
            task_info.pop(1)
            inner_dict = {}
            for _index in range(len(inner_key)):
                key = inner_key[_index]
                if key == 'INFO':
                    inner_dict[key] = ipso[task_info[_index]]
                else:
                    inner_dict[key] = task_info[_index]
            configuration_dict['%s:%s'%(prb_id, task_id)] = inner_dict
    configuration_df  = configuration_dict.items()
    configuration_df = pd.DataFrame(list(configuration_df),columns=['key', 'value']).set_index("key")
    log.Logger('\n'+str(configuration_df), timestamp=0)
    return configuration_dict


def package_upload(serial, filepath, target_file = "rak2560-probe-app.bin", prefix = 'x'):
    file_list = [f for f in os.listdir(filepath) if f.startswith(prefix)]
    sorted_file_list = sorted(file_list)
    target_file = '%s/%s'%(filepath, target_file)

    with open(target_file, 'rb') as file:
        checksum = hex(zlib.crc32(file.read()))
    
    for i in range(2):
        log.Logger('\tFile checkSum = %s'%checksum, fore='MAGENTA', timestamp=0)
        if String_Handling.grep_return('atc+dfufchk=?', serial) in checksum:
            log.Logger('\tpackage_upload successfully', fore='GREEN', timestamp=0)
            return True
        else:
            log.Logger('\tCheckSum is incorrect', fore='RED', timestamp=0)
        if i == 1:
            return False
        offset = 0
        for filename in sorted_file_list:
            filename = '%s/%s'%(filepath, filename)
            f_size = os.path.getsize(filename)
            offset += 1
            while True:
                with open(filename, 'rb') as f:
                    serial.write('ATC+DFUFILE=%s:%s'%(offset,f_size), '>', makeTrue=1)
                    time.sleep(0.1)
                    if serial.write(f.read(), 'OK', encode=0):
                        time.sleep(0.3)
                        break
    with open(target_file, 'r') as file:
        serial.write('atc+dfusize=%s'%(os.path.getsize(target_file)), 'OK')


