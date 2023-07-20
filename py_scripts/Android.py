import src.colorLog as log
import allure
import time
import os
import locale




def get_brand():
    brand = ''
    command = os.popen('adb shell getprop | grep "product.brand"')
    while True:
        tmp = command.buffer.readline().decode(locale.getdefaultlocale()[1], 'ignore')
        if tmp == '':
            break
        else:
            brand += tmp
    return brand

def accept_paring_request(driver):
    appium = driver
    paring_cfm=0
    for i in range(3):
        Pairing_request=0
        if paring_cfm==2:
            break
        if 'samsung' in get_brand():
            Pairing_request=1
        else:
            appium.Action('cmd', 'statusbar expand-notifications', wait=1)
            if appium.Action('text','Pairing request', 'click', max_elem_locate=1):
                Pairing_request=1
        if Pairing_request==1 and appium.Action('id', 'android:id/button1', 'click'):
            paring_cfm += 1
        else:
            time.sleep(1)
    appium.Action('cmd', 'statusbar collapse',wait=0.5)


@allure.step("NFC Tools to Write")
def NFC_Write(driver, cmd):
    appium = driver
    if cmd == appium.Action('id', 'com.wakdev.wdnfc:id/baseline', ['grep', 'text'], wait=0, max_elem_locate=0):
        None
    else:
        appium.Action('url', 'com.wakdev.wdnfc/com.wakdev.nfctools.free.views.MainActivityFree', wait=3)
        appium.Action('text', 'No thanks!', 'click', max_elem_locate=0, wait=0)
        appium.Action('text', 'WRITE', 'click')
        appium.Action('text', 'Add a record', 'click')
        appium.Action('text', 'Add a text record', 'click')
        appium.Action('id', 'com.wakdev.wdnfc:id/text_record', ['key', cmd])
        appium.Action('text', 'OK', 'click')
    appium.Action('id', 'com.wakdev.wdnfc:id/write_button', 'click')
    for i in range(10):
        time.sleep(2)
        text = appium.Action('id', 'com.wakdev.wdnfc:id/dialog_text', ['grep', 'text'], max_elem_locate=0)
        if text == 'Write complete!' or text == 'Write error!':
            break
    if text != 'Write complete!':
        log.Logger('Write ATC+BTADV Failed', 'RED')
        text = False
    return text


def Toggle_BLE(driver):
    log.Logger('*** Toggle BLE', 'BLACK', 'WHITE', 0)
    appium = driver 
    appium.Action('am start', '-a android.bluetooth.adapter.action.REQUEST_DISABLE')
    appium.Action('text', 'Allow', 'click', max_elem_locate=0)
    appium.Action('am start', '-a android.bluetooth.adapter.action.REQUEST_ENABLE')
    appium.Action('text', 'Allow', 'click')



def Forget_All_BLE(driver):
    log.Logger('*** Forget all paring BLE', 'BLACK', 'WHITE', 0)
    appium = driver 
    '''if 'samsung' in get_brand():
        appium.Action('url', 'com.android.settings/com.android.settings.Settings')
        appium.Action('text', 'Connections', 'click')
        dev_list_page = 'Bluetooth'
        deviceDetails = 'com.android.settings:id/deviceDetails'
        Unpair = 'Unpair'
    else:'''
    appium.Action('url', 'no.nordicsemi.android.mcp/no.nordicsemi.android.mcp.MainActivity')
    dev_list_page = 'BONDED'
    deviceDetails = 'no.nordicsemi.android.mcp:id/action_connect_more'
    Unpair = 'Delete bond information'

    appium.Action('text', dev_list_page, 'click', wait=3)
    while True:
        if not appium.Action('id', deviceDetails, 'click', max_elem_locate=0, wait=0):
            break
        appium.Action('text', Unpair, 'click', max_elem_locate=2)


def Paring_BLE_Pixel(driver, dev_name):
    log.Logger('*** Paring BLE with %s' %dev_name, 'BLACK', 'WHITE', 0)
    appium = driver 
    while True:
        appium.Action('url', 'com.android.settings/com.android.settings.Settings')
        appium.Action('text', 'Connected devices', 'click', wait=3)
        if appium.Action('text', 'Pair new device', 'click', wait=6, max_elem_locate=2):
            break
    for i in range(3):
        if appium.Action('text', dev_name, 'click', wait=6, max_elem_locate=0) and \
           appium.Action('id', 'android:id/button1', 'click', max_elem_locate=2) :
            if appium.Action('text', 'USB', action='') and appium.Action('text', dev_name, action=''):
                return True
        else:
            appium.Swipe(x_from=1/2, y_from=9/10, x_to=1/2, y_to=3/10, duration=1000)
    return False


def Paring_BLE(driver, filter_name, service='Nordic UART Service', app='nrf'):
    log.Logger('*** Paring BLE with %s' %filter_name, 'BLACK', 'WHITE', 0)
    appium = driver 
    if app == 'wistoolbox':
        appium.Action('url', 'com.rak.wistoolbox/com.zoontek.rnbootsplash.RNBootSplashActivity')
        appium.Action('id', 'com.rak.wistoolbox:id/ConnectingDeviceEmptyState_connecting_device_empty_state:connect_btn', 'click')
        appium.Action('id', 'com.rak.wistoolbox:id/DeviceSelectionList_WisDuo_LPWAN_Module', 'click')
        appium.Action('id', 'com.rak.wistoolbox:id/DeviceSelectionDetails_device_selection:device_selection_details:connect_btn', 'click')
        for i in range(20):
            if appium.Action('id', 'com.rak.wistoolbox:id/ConnectingDevice_%s'%filter_name, '', max_elem_locate=0):
                break
            elif i < 10:
                log.Logger('\tDUT is not in scan list, wait 1 sec.', 'RED', timestamp=0)
                time.sleep(1)
            else:
                return False
        for i in range(15):
            if filter_name == appium.Action('class', 'android.widget.TextView', ['grep', 'text'], plural=i, max_elem_locate=0):
                appium.Action('class', 'android.widget.TextView', 'click', plural=i+2)
                time.sleep(3)
                break
            elif i == 14:
                log.Logger('\tCan not find the button of "Connect".', 'RED', timestamp=0)
                return False

    else:    
        appium.Action('url', 'no.nordicsemi.android.mcp/no.nordicsemi.android.mcp.MainActivity')
        log.Logger('Android Phone : Filter ' + filter_name)
        text = appium.Action('id', 'no.nordicsemi.android.mcp:id/filter_header', ['grep', 'text'], max_elem_locate=0, wait=0)
        if str(text) == filter_name.lower():
            appium.Swipe(x_from=1/2, y_from=5/10, x_to=1/2, y_to=9/10, duration=1000)
        else:
            appium.Action('id', 'no.nordicsemi.android.mcp:id/filter_header', 'click')
            appium.Action('id', 'no.nordicsemi.android.mcp:id/filter', ['key', filter_name])
            appium.Action('id', 'no.nordicsemi.android.mcp:id/filter_header', 'click', wait=3)
        for i in range(3):
            if appium.Action('id', 'no.nordicsemi.android.mcp:id/display_name', ['grep', 'text'], max_elem_locate=1, wait=0):
                appium.Action('text','CONNECT', 'click', max_elem_locate=0, wait=2)
                break
            elif i == 2:
                log.Logger('\tCan not find the BLE Device.', 'RED', timestamp=0)
                return False
            else:
                log.Logger('\tDUT is not in scan list, wait 1 sec', 'RED', timestamp=0)
                appium.Swipe(x_from=1/2, y_from=5/10, x_to=1/2, y_to=9/10, duration=1000)
                time.sleep(1)
    if filter_name != 'DfuTarg':
        accept_paring_request(appium)
    
    result = False
    if app == 'wistoolbox':
        time.sleep(2)
        if appium.Action('text', 'Select device_name', '', max_elem_locate=0):
            return False
        service = 'Device'
        check_time = 10
    else:
        check_time=3
    if appium.Action('text', service, 'click', max_elem_locate=check_time):
        return True
    return result



def DFU_over_nRF(driver, package):
    log.Logger('*** DFU over BLE %s' %package, 'BLACK', 'WHITE', 0)
    appium = driver
    #if appium.Action('text', 'Value: Indications enabled','' , max_elem_locate=0, wait=0):
    appium.Action('id', 'no.nordicsemi.android.mcp:id/action_stop_indications', 'click', max_elem_locate=0)
    appium.Action('id', 'no.nordicsemi.android.mcp:id/action_start_indications', 'click')
    appium.Action('id', 'no.nordicsemi.android.mcp:id/action_write', 'click')
    if appium.Action('text', 'SEND', 'click', wait=2) == False or Paring_BLE(appium, 'DfuTarg', service='Secure DFU Service') == False:
        return False
    appium.Action('id', 'no.nordicsemi.android.mcp:id/action_dfu', 'click', wait=3)
    appium.Action('text', 'Distribution packet (ZIP)', 'click')
    appium.Action('id', 'android:id/button1', 'click', wait=2)
    appium.Action('content_desc', 'Show roots', 'click')
    appium.Action('text', 'Downloads', 'click', plural=-1)
    appium.Action('id', 'com.google.android.documentsui:id/option_menu_search', 'click')
    appium.Action('id', 'com.google.android.documentsui:id/search_src_text', ['key', package])
    appium.Action('text', package, 'click', plural=-1)
    time.sleep(30)
    picture = appium.ScreenShot('DFU')
    allure.attach.file(picture, attachment_type=allure.attachment_type.JPG)
    while True:
        if not appium.Action('text', 'UPLOADING…', '', max_elem_locate=0, wait=0):
            time.sleep(10)
            return True
    return False





@allure.step("nRF_UART and Parsing")
def BLE_UART(driver, device_name, cmd, wait=0):
    log.Logger('@@@ ' + cmd, 'BLACK', 'WHITE', 0)
    appium = driver
    if not appium.Action('content_desc', 'Clear items.', 'click', wait=0, max_elem_locate=0):
        appium.Action('url', 'no.nordicsemi.android.nrftoolbox/no.nordicsemi.android.nrftoolbox.MainActivity', wait=2)
        appium.Swipe(x_from=1/2, y_from=9/10, x_to=1/2, y_to=3/10, duration=200)
        appium.Action('text', 'Universal Asynchronous Receiver/Transmitter (UART)', 'click')
        appium.Action('text', device_name, 'click', wait=4)
    if not appium.Action('text', 'Text to send', 'click'):
        return False
    appium.Action('input', 'text "%s"' %cmd, wait=0)
    appium.Action('input', 'keyevent 66', wait=0)
    #appium.Action('input', 'keyevent 66')
    appium.Action('text', 'Send', 'click')
    appium.hide_keyboard()
    #appium.Action('url', 'no.nordicsemi.android.log/no.nordicsemi.android.logger.MainActivity', wait=2)
    #appium.Action('id', 'no.nordicsemi.android.log:id/name', 'click')
    time.sleep(wait)
    index=0
    text_list=['Error']
    while True:
        text = appium.Action('class', 'android.widget.TextView', ['grep', 'text'], max_elem_locate=0, plural=index)
        if text == False:
            break
        else:
            text_list.append(text.replace('\r\n',' ').replace('\r', ''))
        index += 1
    return text_list



@allure.step("nRF_UART and Parsing")
def BLE_UART_WisToolBox(driver, device_name, cmd, wait=0):
    log.Logger('@@@ ' + cmd, 'BLACK', 'WHITE', 0)
    appium = driver
    if appium.Action('id', 'com.rak.wistoolbox:id/Terminal_terminal:clear_btn:text:terminal:clear', 'click', wait=0, max_elem_locate=0):
        pass
    else:
        locate_bound = ['[1271,172][1344,246]', '[958,152][1008,203]', '[954,128][1008,183]']
        log.Logger('Hard code to locate "Top right element" %s'%locate_bound, 'BLACK', 'WHITE', timestamp=0)
        for i in range(100):
            bounds = appium.Action('class', 'android.widget.TextView', ['grep', 'bounds'], wait=0,plural=i)
            if any(bounds in ele for ele in locate_bound) :
                appium.Action('class', 'android.widget.TextView', 'click', plural=i)
                break
            elif i == 40:
                log.Logger('Hard code to locate "Top right element", Failed', 'RED', '',timestamp=0)
                return False

        appium.Action('id', 'com.rak.wistoolbox:id/DeviceInfoSettings_advanced_commands_modal:advance_mode_commands_option', 'click')
        appium.Action('id', 'com.rak.wistoolbox:id/AdvancedMode_advanced_commands:console_btn', 'click')
    appium.Action('id', 'com.rak.wistoolbox:id/Terminal_terminal:input', ['key', cmd], wait=0)
    appium.Action('input', 'keyevent 66', wait=0)
    #appium.Action('input', 'text "%s"' %cmd)
    appium.Action('id', 'com.rak.wistoolbox:id/Terminal_terminal:send_btn', 'click')
    time.sleep(wait)
    index=-1
    text_list=['Error']
    while True:
        text = appium.Action('class', 'android.widget.TextView', ['grep', 'text'], max_elem_locate=0, plural=index)
        if text == False:
            break
        else:
            text_list.append(text.replace('\r\n',' ').replace('\r', ''))
        index -= 1
    return text_list
