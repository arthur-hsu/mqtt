from appium import webdriver as appdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.by import By
import time, threading

#----- import Self Module -----#
import config.config as cf
#initlogpath = settings.initlogpath
from . import commonFunction as commonFunction  
import os
config_path = os.path.abspath(os.path.dirname(__file__)) + '/config/'
from . import colorLog as log



stopScript = 0


class Appium_Server:
    def Run(self):
        commonFunction.killProcess('node')
        desired_caps = {}
        deviceName = getPhoneID()
        desired_caps['deviceName'] = deviceName
        android_ver = Adb_Shell(deviceName, 'shell getprop ro.build.version.release')
        desired_caps['platformVersion'] = android_ver

        self.AppiumIsReady = 0 
        AppiumServer = threading.Thread(target = self.AppiumServer, args=() )
        AppiumServer.daemon = True
        AppiumServer.start()
        while self.AppiumIsReady == 0 :
            time.sleep(1)

        log.Logger('Connecting Android...')
        desired_caps['platformName'] = 'Android'
        desired_caps['newCommandTimeout']= '20000'
        desired_caps['unicodeKeyboard']= False
        desired_caps['resetKeyboard'] = False
        desired_caps['noSign']= True
        #desired_caps['autoLaunch'] = False
        desired_caps['automationName'] = 'Uiautomator2'
        for i in range(3):
            try:
                self.app_driver = appdriver.Remote('http://127.0.0.1:4723/wd/hub', desired_caps)
            except Exception as e:
                if i < 2:
                    log.Logger('Can not access Android Phone, try again...')
                else:
                    log.Logger(str(e))
                    log.Logger('Failed, Stop the process, please reconnect the USB of Android and run again.')
                    return False
        self.app_driver.implicitly_wait(3)
        self.app_driver.update_settings({"waitForIdleTimeout": 100})
        return self.app_driver




    def AppiumServer(self):
        log.Logger("**** appium -a 127.0.0.1 -p 4723 -bp 4724 --chromedriver-port 9515 --session-override", 'BLACK', 'WHITE', timestamp=0)
        AppiumServer = os.popen("appium -a 127.0.0.1 -p 4723 -bp 4724 --chromedriver-port 9515 --session-override")
        while True: 
            try:
                tmp = AppiumServer.buffer.readline().decode('ascii', 'ignore').replace('\r','').replace('\n','')
            except Exception as e:
                log.Logger(str(e))
                return
            if self.AppiumIsReady == 0:
                log.Logger(tmp)
                if 'listener started on 127.0.0.1' in tmp:
                    self.AppiumIsReady = 1




class Appium_Module:
    def __init__(self, driver=''):
        global stopScript
        if driver != '':
            self.app_driver = driver
        else:
            self.app_driver = cf.get_value('driver')
        self.deviceName = getPhoneID()
        self.app_driver.orientation = "PORTRAIT"
        self.W = self.app_driver.get_window_size()['width']
        self.H = self.app_driver.get_window_size()['height']


    def Disconnect(self):
        try:
            self.app_driver.quit()
            time.sleep(1)
            commonFunction.killProcess('node')
        except:
            None
    
    def hide_keyboard(self):
        Adb_Shell(deviceName=self.deviceName, text='shell input keyevent 111')



    def Action(self, find_by, element, action='', wait=1, plural=0, max_elem_locate=3):
        global stopScript
        elemType = {'id': By.ID, 'text': By.XPATH, 'class': By.CLASS_NAME, 'name': By.NAME, 'content_desc': AppiumBy.ACCESSIBILITY_ID}
        ##By.ID : resource id
        if 'key' in action:
            log.Logger('Android Phone : Send Key %s' %action[1])
        elif action == 'click':
            if find_by == 'id':
                tmp_element = element.split('/')[-1].split(':')[-1]
            elif find_by == 'class':
                tmp_element = element.split('.')[-1].split(':')[-1]
            else:
                tmp_element = element
            log.Logger('Android Phone : Click %s' %tmp_element)
        elif action == 'terminate':
            log.Logger('Android Phone : terminate "%s"'%element)

        if find_by == 'text':
            element = "//*[contains(@text, '%s')]" %element
        for i in range(40):
            if stopScript == 1 :
                return False
            if find_by in elemType:
                elem = self.app_driver.find_elements(elemType[find_by], element)
                plural = int(plural)
                if (plural < 0 and len(elem) >= abs(plural)) or (plural >= 0 and len(elem) > plural):
                    elem = elem[plural]
                    break
                else:
                    if max_elem_locate == 0:
                        return False
                    elif i == max_elem_locate :
                        if type(action) == type([]):
                            tmp = action[0]
                        else:
                            tmp = action
                        log.Logger('*** Can not %s, with "%s" & "%s" & "plural=%s"' %(tmp, find_by, element, str(plural)), 'RED' , timestamp=0)
                        return False

            elif find_by == 'url':
                Adb_Shell(deviceName=self.deviceName, text='shell cmd statusbar collapse', prn=0)
                Adb_Shell(deviceName=self.deviceName, text='shell am start -W -n %s -S' %element, prn=0)
                self.app_driver.orientation = "PORTRAIT"
                time.sleep(wait)
                return True

            elif find_by == 'input':
                Adb_Shell(deviceName=self.deviceName, text='shell input %s' %element, prn=0)
                time.sleep(wait)
                return True

            elif find_by == 'cmd' or find_by == 'am start':
                Adb_Shell(deviceName=self.deviceName, text='shell %s %s' %(find_by, element), prn=0)
                time.sleep(wait)
                return True

            elif find_by == 'adb':
                Adb_Shell(deviceName=self.deviceName, text='%s' %element, prn=0)
                time.sleep(wait)
                return True

        for i in range(30):
            try:
                if stopScript == 1 :
                    return False
                ### action
                if action == 'click':
                    elem.click()
                elif action == 'tap':
                    self.app_driver.tap([element],500) ### when tap, element need tuple like (540, 903)
                elif 'clear' in action : 
                    elem.clear()
                elif 'key' in action:
                    elem.clear()
                    if action[1] != '':
                        elem.send_keys(action[1])
                elif action == 'back': 
                    self.app_driver.back()
                elif action == 'terminate': 
                    self.app_driver.terminate_app(element)
                
                elif 'grep' in action :
                    value = elem.get_attribute(action[1])
                    '''if action[1] == 'bounds':
                        value = value.split('][')
                        value[0] = value[0].replace('[','').split(',')
                        value[1] = value[1].replace(']','').split(',')
                        value = [(int(value[0][0]) + int(value[1][0]))/2, (int(value[0][1]) + int(value[1][1]))/2]'''
                    log.Logger('\t\tGrep %s : %s' %(action[1], str(value)), timestamp=0)
                    return value
                time.sleep(wait)
                return True
            except Exception as e:
                if 'do not exist in DOM anymore' in str(e):
                    log.Logger('*** Element do not exist in DOM anymore', 'RED', timestamp=0)
                    return False
                elif i == 25:
                    log.Logger('*** Error : %s' %str(e), 'RED', timestamp=0)
                    return False
                time.sleep(1)

    def ScreenShot(self, name=''):
        log.Logger(' ScreenShot the phone picture "%s"'%name, fore='GREEN', timestamp=0)
        # 從全域性變數取截圖資料夾位置
        shotTime = time.strftime( "%Y-%m-%d %X", time.localtime() )
        path = cf.get_value('screenshot_path')
        savename = '%s_%s.png' %(str(shotTime), name)
        escape_string = [":", " ", '"', "$", '\\n', '?']
        for string in escape_string:
            savename = savename.replace(string, "")
        saveto = path + savename 
        self.app_driver.get_screenshot_as_file(saveto)
        return saveto
        


    def Swipe(self, x_from, y_from, x_to, y_to, duration, location=0):
        log.Logger('Swipe Screen.')
        self.app_driver.hide_keyboard()
        for i in range(3):
            try:
                if stopScript == 1 :
                    return False
                if location == 0:
                    #self.app_driver.swipe(x_from*self.W, y_from*self.H, x_to*self.W, y_to*self.H, duration)
                    Adb_Shell(deviceName=self.deviceName, text='shell input swipe %d %d %d %d %d'%(x_from*self.W, y_from*self.H, x_to*self.W, y_to*self.H, duration))
                else:
                    self.app_driver.swipe(x_from, y_from, x_to, y_to, duration)
                    '''elem = self.driver.find_element_by_xpath("//*[contains(@text, 'Application Key 1')]")
                    tmp = elem.location
                    self.driver.swipe(tmp['x'], tmp['y'], 7/10*W, tmp['y'])'''
                return True
            except:
                time.sleep(1)
        return False




    def Forget_All_Wifi(self):
        log.Logger("**** Forget all wifi", 'BLACK', 'WHITE', timestamp=0)
        Adb_Shell(deviceName=self.deviceName, text='shell svc wifi enable', expected='', prn=0)
        #Adb_Shell(deviceName=self.deviceName, text='shell svc wifi disable', expected='', prn=0)
        self.Action('url', 'com.android.settings/com.android.settings.Settings')
        #self.Action('text', 'Connections', 'click', max_elem_locate=1)
        self.Action('text', 'Connections', 'click')
        self.Action('text', 'Wi-Fi', 'click')
        self.Action('content_desc', 'More options', 'click')
        #self.Action('text', 'Advanced', 'click', max_elem_locate=1 )
        if not self.Action('text', 'Advanced', 'click'):
            log.Logger('No Saved Networks')
            return True
        self.Swipe(x_from=1/2, y_from=7/10, x_to=1/2, y_to=1/10, duration=1000)
        self.Action('text', 'Manage networks', 'click')
        self.Action('text', 'Delete', 'click', wait=2)
        if  self.Action('id', 'com.android.settings:id/select_all_checkbox', ['grep', 'checked']) == 'false':
            self.Action('id', 'com.android.settings:id/select_all_checkbox', 'click')
            #self.Action('text', 'Delete', 'click', wait=2)
            self.Action('id', 'com.android.settings:id/navigation_bar_item_small_label_view', 'click', wait=2)
        else:
            while self.Action('id', 'android:id/title', 'click', wait=1, max_elem_locate=0): 
                self.Action('text', 'FORGET', 'click')
        log.Logger("Cleaned all saved networks", fore='GREEN')
        self.Action('', 'com.android.settings', 'terminate')
        return True



    def Connect_To_Wifi(self, ssid, password):
        while True:
            if stopScript == 1 :
                return False
            log.Logger('**** Config Phone wifi %s/%s' %(ssid, password), fore='BLACK', back='WHITE', timestamp=0)
            self.Action('url', 'com.android.settings/com.android.settings.Settings')
            self.Action('text', 'Connections', 'click', max_elem_locate=0)
            self.Action('text', 'Wi-Fi', 'click')
            for i in range(15):
                if self.Action('text', 'Add network', 'click', wait=0, max_elem_locate=0):
                    time.sleep(1)
                    break
                else:
                    self.Swipe(x_from=1/2, y_from=7/10, x_to=1/2, y_to=1/10, duration=50)
            self.Action('id', 'com.android.settings:id/edittext', ['key', ssid])
            if password != '':
                self.Action('text', 'WPA/WPA2', 'click')
                self.Action('text', 'WPA/WPA2-Personal', 'click')
                self.Action('id', 'com.android.settings:id/edittext', ['key', password], plural=1)
                self.Action('text', 'Save', 'click')
            for i in range(15):
                if self.Action('text', 'Connected', '', max_elem_locate=0) or self.Action('text', 'may not be available', '', max_elem_locate=0):
                    log.Logger('Connected', 'GREEN')
                    return True
                else:
                    self.Swipe(x_from=1/2, y_from=3/10, x_to=1/2, y_to=9/10, duration=200)
    



def Adb_Shell(deviceName, text, expected = 'None', prn=1):
    if deviceName =='':
        deviceName = self.deviceName
    cmd = 'adb -s %s %s' %(deviceName, text)
    log.Logger(cmd)
    adb_cmd = os.popen(cmd)
    log_list = []
    while True:
        tmp = adb_cmd.buffer.readline().decode('ascii', 'ignore')
        handle = tmp.replace('\n','').replace('\r','')
        if prn == 1:
            log.Logger(handle)
        log_list.append(handle)
        if expected in handle or tmp == '':
            break
    #time.sleep(1)
    return log_list[-1]
#Adb_Shell('am start -W -n no.nordicsemi.android.mcp/no.nordicsemi.android.mcp.DeviceListActivity -S')
#Adb_Shell(input text 123')
# Notify
# adb shell am start -a android.bluetooth.adapter.action.REQUEST_ENABLE
'''adb shell cmd statusbar expand-notifications
adb shell cmd statusbar collapse
adb shell cmd statusbar expand-settings
more info
adb shell cmd statusbar help'''


def getPhoneID():
    cmd = 'adb devices'
    command = os.popen(cmd)
    while True:
        tmp = command.buffer.readline().decode('ascii', 'ignore')
        if tmp == '':
            log.Logger('\nCan not find SmartPhone, please reconnect the USB.')
            input("\tInput any key to rerun.")
            command = os.popen(cmd)
        else:
            tmp = tmp.replace('\n','').replace('\r','')
            log.Logger(tmp)
        if "device" in tmp and 'List of devices attached' not in tmp:
            # 轉換成list
            #ex. ['6caf4753', 'device\n']
            PhoneID = tmp.split('\t')
            PhoneID = PhoneID[0]
            command.close()
            return PhoneID








'''
抓取app packet
adb logcat | grep 'Displayed'
Displayed com.wakdev.wdnfc/com.wakdev.nfctools.views.records.ChooseRecordActivity: +71ms
(/前面那段是packet)

抓取app的active
/Users/reesehung/Library/Android/sdk/build-tools/29.0.1/aapt2 dump badging apk
這一行launchable-activity: name='com.zoontek.rnbootsplash.RNBootSplashActivity'

adb -s 98291FFBA0053T shell am start -W -n name/active -S
adb -s 98291FFBA0053T shell am start -W -n com.wakdev.wdnfc/com.wakdev.nfctools.free.views.MainActivityFree -S
'''
