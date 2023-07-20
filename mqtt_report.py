import datetime
import json
import os, re
import sys
import threading
import time
import pandas as pd
import pytz
from dateutil import parser

import config.config as cf
import src.colorLog as log
import src.mqtt_lib as mqtt_lib
import src.pandas_lib as pd_write
from src.mail_lib import send_mail
import src.python_excel as python_excel
######################################################################################################################
dut_uplink_intv = 180
avg_list        = ['Rssi','SNR','Temperature','Humid']
sendto          =['arthur.hsu.rak@gmail.com', 'kerry.hsu@rakwireless.com','reese.hung@rakwireless.com','ptrose.liu@rakwireless.com','booker.chang@rakwireless.com','wade.luo@rakwireless.com']
mail_send_time  = [8,0,0] # [hour, min, second]
dev_dict        ={ # device set in this dict
    'HUB'               : {'app_index' : '2c5c5532-77ea-46b9-90e0-c2f3a7b74efd', 'DevEUI' : '6bb38dd1b5f62ae9'},
    'test'              : {'app_index' : '6da8ceee-bcb1-4c83-9ac6-6beeb27f6209', 'DevEUI' : '1111eeee1111eeee'},
    'BridgeIO'          : {'app_index' : '2c5c5532-77ea-46b9-90e0-c2f3a7b74efd', 'DevEUI' : '3193430938326042'},
}
######################################################################################################################
# python3 mqtt_report.py 4631
if __name__ == '__main__':
    target='HUB'
    if len(sys.argv)>1 : target = str(sys.argv[1])
    if len(sys.argv)>2 : dut_uplink_intv = int(sys.argv[2])
    if sys.argv[1] == 'test':
        target = 'test'
        dut_uplink_intv = 10
        sendto = ['arthur.hsu.rak@gmail.com']
    print(f'{sys.argv=}')
df , columns , dict_tmp= pd.DataFrame(columns=[]) , [] , {}
opentime            = time.strftime( "%Y.%m.%d", time.localtime() ).replace(":", "")
WORK_FILE           = os.getcwd()
LOG_Folder          = os.path.join(WORK_FILE,'Test_result')
if not os.path.isdir(LOG_Folder):os.mkdir(LOG_Folder)
filename            = os.path.basename(__file__).replace('.py','')
os.chdir(LOG_Folder)
REPORT              = os.path.join(LOG_Folder, '%s-%s_%s.xlsx'%(opentime, target, filename))
os.chdir(WORK_FILE)
remote_ip       = '127.0.0.1'
loop_forever    = 1
excel_writer    = pd.ExcelWriter(REPORT)
cf.init()
log.Logger('Send reports at %s per day.'%(str(mail_send_time).strip('[]').replace(',',':')),'BLACK','WHITE',timestamp=0)
log.Logger(f'{sendto= }','BLACK','WHITE',timestamp=0)
log.Logger('Mqtt subscribe %s'%target,'BLACK','WHITE', 0)
target_dict = dev_dict[target]

mqtt                = mqtt_lib.MQTT_Module(remote_ip, appID= target_dict['app_index'], devEUI= target_dict['DevEUI'], sub_topic='', pub_topic='', client_id='username', client_pw='password')
mqtt_task           = threading.Thread(target=mqtt.subscribe, args=(loop_forever, 10))
mqtt_task.daemon    = True
mqtt_task.start()

def show_table():
    print('table task running')
    while True : log.colo_prt('\t\t\t\tSHOW TABLE\n%s'%df , "BLUE", "WHITE",timestamp=0) if input().lower() == 'df' else log.colo_prt("Type 'df' would show table.","BLUE","WHITE",0)
table_task          = threading.Thread(target= show_table)
table_task.daemon   = True
table_task.start()



while True:
    try:
        data=mqtt.getdata()
        if data is not None:
            # print(json.dumps(data, sort_keys=True, indent=4, separators=(', ', ': ')))
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            dict_tmp['Time']            = now
            if 'channel' in data['rxInfo'][0]:
                dict_tmp['Uplink_channel']  = data['rxInfo'][0]['channel']
            else:
                dict_tmp['Uplink_channel']  = ''
            dict_tmp['SF']                  = data['txInfo']['modulation']['lora']['spreadingFactor']
            dict_tmp['Rssi']                = data['rxInfo'][0]['rssi']
            dict_tmp['SNR']                 = data['rxInfo'][0]['snr']
            dict_tmp['FCnt']                = data['fCnt']
            dict_tmp['Data']                = data['data']
            if 'temperature' in data['object']['RESULT'].keys(): dict_tmp['Temperature']        = '%s'   %(data['object']['RESULT']['temperature']/10)
            if 'humid' in data['object']['RESULT'].keys(): dict_tmp['Humid']                    = '%s'   %(data['object']['RESULT']['humid'])
            columns= list(dict_tmp.keys())
            df=pd_write.write(df, dict_tmp, columns)
            print(json.dumps(dict_tmp, indent=4, separators=(', ', ': ')))#sort_keys=True
            dict_tmp.clear()
        time.sleep(1)
    except KeyboardInterrupt: 
        if df.empty!=True   : pd_write.save_to_excel(df,excel_writer,columns)
        pythonexcel = python_excel.python_excel(REPORT, avg_list, dut_uplink_intv)
        pythonexcel.test()
        send_mail(sendto, REPORT, opentime, target)
        sys.exit('KeyboardInterrupt')
    except Exception as e:
        print('Error len : %s, %s'%(e.__traceback__.tb_lineno, e))
        continue
    now = datetime.datetime.now()
    nowtime=[now.hour,now.minute,now.second]
    #print(nowtime)
    if nowtime == mail_send_time:
        #print(nowtime)
        if df.empty  != True   : pd_write.save_to_excel(df,excel_writer,columns)
        # Analysis      = Analysis_report.analysis_report(dut_uplink_intv, REPORT)
        # Analysis.analysis(avg_list)
        pythonexcel = python_excel.python_excel(REPORT, avg_list, dut_uplink_intv)
        pythonexcel.test()
        mail_task = threading.Thread(target=send_mail,args=(sendto, REPORT, opentime, target))
        mail_task.daemon=True
        mail_task.start()
        df , columns , dict_tmp = pd.DataFrame(columns=[]) , [] , {}
        opentime                = time.strftime( "%Y.%m.%d_%X", time.localtime() ).replace(":", "")
        os.chdir(LOG_Folder)
        REPORT                  = os.path.join(LOG_Folder, '%s-%s.xlsx'%(opentime, filename))
        excel_writer            = pd.ExcelWriter(REPORT)
        os.chdir(WORK_FILE)
