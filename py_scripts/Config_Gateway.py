import src.colorLog as log
import src.paramiko_lib as paramiko_lib
import src.selenium_lib as selenium_lib
import allure
import config.config as cf
import time, re
import json

with open('topo/band_info.json', 'r') as f:
    band_dict = json.load(f)


def SSH_Object(remote_ip):
    ssh = paramiko_lib.SSH_Module(remote_ip, username='root', password='root',)
    return ssh



@allure.step("Set LoRA Network")
def Set_LoRA(remote_ip, app_index, appeui, appkey, DevEUI, daddr, connect_type, cls, band, subband): 
    log.Logger('Set LoRA Nwtwork', 'BLACK', 'WHITE', 0)
    Application(remote_ip, app_index, appeui, appkey, DevEUI, daddr, connect_type, cls)
    driver = selenium_lib.Selenium_Server().Run()
    if not driver:
        log.Logger("Can not Run WebDriver.\n\n\n\n")
        return False
    #cf.set_value('driver', driver.Run())
    driver = selenium_lib.Selenium_Module(driver)
    result = Set_SubBand(driver, 'http://%s/cgi-bin/luci'%remote_ip, band, subband)
    driver.Disconnect()
    if not result:
        log.Logger("Can not Set Channel Plan\n\n\n\n")
        return False
    return True





def Application(remote_ip, app_index, appeui, appkey, DevEUI, daddr, connect_type, cls):
    global ssh
    ssh = paramiko_lib.SSH_Module(remote_ip, username='root', password='root',)
    Del_APP(app_index)
    Reset_Frame_Counter(DevEUI)
    Set_APP(app_index, appeui, appkey, DevEUI, daddr.lower(), connect_type, cls)


def Set_SubBand(driver, url, band, subband):
    log.Logger('*** Set %s, %s' %(band_dict[str(band)]['region'], band_dict[str(band)]['FSB'][str(subband)]), 'BLACK', 'WHITE',0)
    if not driver.Action('url', url) :
        return False
    driver.Action('name', 'luci_password', ['key', 'root'])
    driver.Action('class', 'cbi-button-apply', 'click')
    driver.Action('class', 'icon-Channel', 'click')
    if subband == 'None':
        fsb = driver.Action('class', 'cbi-button-reset', 'click')
    else:
        driver.Action('name', 'cbid.lora_pkt_fwd.freq_plan.region', band_dict[str(band)]['region'])
        fsb = driver.Action('name', 'cbid.lora_pkt_fwd.freq_plan.FSB', ['select', band_dict[str(band)]['FSB'][str(subband)]])
    result = driver.Action('name', 'cbi.apply', 'click', wait=3)
    driver.Action('class', 'pull-right', 'click')
    return result




def Reset_Frame_Counter(DevEUI, ssh_object=''):
    global ssh
    log.Logger('Reset frame counter', 'BLACK', 'WHITE',0)
    if ssh_object != '':
        ssh = ssh_object
    ssh.send_command("srvctrl -c %s"%DevEUI)
    time.sleep(3)


def Del_APP(app_index, ssh_object=''):
    global ssh
    #remove the app
    log.Logger('Del all device in app_index_%s'%app_index, 'BLACK', 'WHITE',0)
    if ssh_object != '':
        ssh = ssh_object
    pre_appkey = ssh.send_command('uci show lorasrv | grep "lorasrv.app_%s.app_key="' % app_index, dump=1)
    pre_appkey = re.findall( "lorasrv.app_%s.app_key='([^?].*)'"%app_index, pre_appkey) 
    if len(pre_appkey)>0 :
        ssh.send_command('uci del lorasrv.app_%s' % app_index)
        pre_deveui = ssh.send_command('uci show lorasrv | grep "app_key=%s%s%s"' %("'" ,pre_appkey[0].replace('\r','').replace('\n',''), "'"), dump=1)
        pre_deveui = re.findall("lorasrv[.]([^?].*)[.]app_key=", pre_deveui) 
        log.Logger('\tpre_deveui: %s' %pre_deveui, fore='GREEN', timestamp=0)
        if len(pre_deveui)>0:
            for del_deveui in pre_deveui:
                ssh.send_command('uci del lorasrv.%s' % (del_deveui))
    ssh.send_command('uci commit lorasrv')
    ssh.send_command('/etc/init.d/loraserver restart')
    time.sleep(3)

def Set_APP(app_index, appeui, appkey, DevEUI, daddr, connect_type='otaa', cls='A', appskey='', nwkskey='', app_name='app', dev_name='rak', auto_add='0', adr=1, ssh_object=''):
    log.Logger('Set Application to app_index%s/%s' %(app_index, DevEUI), 'BLACK', 'WHITE',0)
    global ssh
    if ssh_object != '':
        ssh = ssh_object
    ssh.send_command('uci set lorasrv.lorasrv.RECEIVE_DELAY1=1')

    date = time.ctime()
    app_name = '%s%s'%(app_name, app_index)
    appPrefix = 'uci set lorasrv.app_%s' %app_index
    log.Logger('\r\nadd app date:%s appkey:%s' % (date, appkey))
    #add config app
    ssh.send_command('%s=app' % (appPrefix))
    ssh.send_command('%s.id=%s' % (appPrefix, app_index))
    ssh.send_command('%s.auth_mode=0' % (appPrefix))
    ssh.send_command('%s.name=%s' % (appPrefix, app_name))
    ssh.send_command('%s.date=\"%s\"' % (appPrefix, date))
    ssh.send_command('%s.auto_add=%s' % (appPrefix, auto_add))
    ssh.send_command('%s.app_key=%s' % (appPrefix, appkey))
    ssh.send_command('%s.PayloadFormat=none' % (appPrefix))
    ssh.send_command('%s.data_encode=base64' % (appPrefix))
    ssh.send_command('%s.http_max_connection=16' % (appPrefix))
    ssh.send_command('%s.http_max_queue=64' % (appPrefix))
    ssh.send_command('uci set lorasrv.lorasrv.app=%s' %app_index)
    ssh.send_command("%s.eui=%s" % (appPrefix, appeui))
    ssh.send_command('uci commit lorasrv')
    #remove the device if it in the application list already
    ssh.send_command('uci del_list lorasrv.app_%s.device=%s' %(app_index, DevEUI))
    ssh.send_command('uci add_list lorasrv.app_%s.device=%s' %(app_index, DevEUI))
    if adr == 0:
        ssh.send_command('uci delete lorasrv.lorasrv.adr_enable')
    # add config device deveui
    devPrefix = 'uci set lorasrv.%s' % DevEUI
    ssh.send_command('%s=device' % devPrefix)
    ssh.send_command('%s.app_key=%s' % (devPrefix, appkey))
    ssh.send_command('%s.mode=%s' % (devPrefix, connect_type.lower()))
    ssh.send_command('%s.disable_app_eui=0' % devPrefix)
    ssh.send_command('%s.Class=%s' % (devPrefix, cls))
    ssh.send_command('%s.name=%s' % (devPrefix, dev_name))
    ssh.send_command('%s.fcntwidth=32' % (devPrefix))
    ssh.send_command('%s.loRaMacVersion=1.0.3' % (devPrefix))
    ssh.send_command('%s.loRaRegionalParamsReversion=A' % (devPrefix))
    if connect_type.lower() == 'abp':
        ssh.send_command("%s.apps_key=%s" % (devPrefix, appskey))
        ssh.send_command("%s.nwks_key=%s" % (devPrefix, nwkskey))
        ssh.send_command("%s.dev_addr=%s" % (devPrefix, daddr))
    ssh.send_command('uci commit lorasrv')
    ssh.send_command('uci set lorawan.network.log_level=7')
    ssh.send_command('uci commit lorawan')
    ssh.send_command('/etc/init.d/loraserver restart')
    time.sleep(3)
    ssh.disconnect()


