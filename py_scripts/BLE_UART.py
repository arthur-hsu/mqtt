import src.colorLog as log
import allure




@allure.step("nRF_UART and Parsing")
def nRF(driver, device_name, cmd):
    log.Logger('@@@ ' + cmd, 'BLACK', 'WHITE', 0)
    appium = driver
    for i in range(4):
        appium.Action('url', 'no.nordicsemi.android.nrftoolbox/no.nordicsemi.android.nrftoolbox.MainActivity', wait=2)
        appium.Swipe(x_from=1/2, y_from=9/10, x_to=1/2, y_to=3/10, duration=1000)
        appium.Action('text', 'Universal Asynchronous Receiver/Transmitter (UART)', 'click')
        appium.Action('text', device_name, 'click', wait=6)
        if appium.Action('text', 'Text to send', 'click'):
            break
        elif i == 3 :
            return False
    appium.Action('input', 'text "%s"' %cmd)
    #appium.Action('input', 'keyevent 66')
    appium.Action('text', 'Send', 'click')
    appium.Action('url', 'no.nordicsemi.android.log/no.nordicsemi.android.logger.MainActivity', wait=2)
    appium.Action('id', 'no.nordicsemi.android.log:id/name', 'click')
    result = 'Error'
    index=0
    while True:
        text = appium.Action('id', 'no.nordicsemi.android.log:id/data', ['grep', 'text'], max_elem_locate=0, plural=index)
        if text == False:
            break
        elif ('ERROR' in text) or ('OK' in text) :
            result = text
        elif ('ATC+' in text or '+EVT' in text) and ('sent' not in text):
            result = text
            break
        index += 1
    #screenshot = appium.ScreenShot(cmd)
    #allure.attach.file(screenshot, attachment_type=allure.attachment_type.JPG)
    result = result.replace('\r\n',' ').replace('\r', '')
    log.Logger('\n\tReturn : '+ result, fore='GREEN', timestamp=0)
    return result
