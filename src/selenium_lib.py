from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert
import config.config as cf
#initlogpath = settings.initlogpath
from . import commonFunction as commonFunction  
import os, time, platform
from . import colorLog as log
#from msedge.selenium_tools import EdgeOptions, Edge


class Selenium_Server:
    def Run(self, headless=1):
        log.Logger("**** Running WebDriver", 'BLACK', 'WHITE', 0)
        commonFunction.killProcess('chromedriver')
        # chrome
        options = webdriver.ChromeOptions()
        #options = webdriver.chrome.options.Options()
        if headless == 1:
            options.add_argument("--headless")
        options.add_argument("-incognito")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        #prefs = {'profile.default_content_settings.popups': 0, 'download.default_directory': cf.get_value('download_path')}
        #options.add_experimental_option('prefs', prefs)
        try:
            '''if 'Darwin' in platform.system():  
                self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            else:'''
            self.driver = webdriver.Chrome(options=options)
            self.driver.maximize_window()
            return self.driver
        except Exception as e:
            log.Logger(str(e))
            log.Logger('Please download the correct version of ChromeDriver.\n(%s)\nsudo apt-get install chromium-chromedriver\n\tor\nbrew install --cask chromedriver', fore='RED', timestamp=0)
            return False
        # Edge
        '''edge_options = EdgeOptions()
        edge_options.use_chromium = True 
        # make Edge headless
        #edge_options.add_argument('headless')
        #edge_options.add_argument('disable-gpu')
        edge_options.add_argument("-incognito")
        self.driver = Edge(executable_path=os.path.abspath(os.path.dirname(__file__))+ '/msedgedriver', options=edge_options)'''


class Selenium_Module:
    def __init__(self, driver=''):
        global stopScript
        if driver != '':
            self.driver = driver
        else:
            self.driver = cf.get_value('driver')

    def Disconnect(self):
        try:
            self.driver.close()
            self.driver.quit()
            commonFunction.killProcess('webdriver')
        except:
            None

    
    def Action(self, find_by, element, action='', wait=1, plural=0, max_elem_locate=3):
        if 'key' in action:
            log.Logger('Selenium : Input "%s"' %action[1])
        elif 'select' in action:
            log.Logger('Selenium : Select "%s"'%action[1])
        elif action == 'click':
            log.Logger('Selenium : Click "%s"' %element)

        elemType = {'link': By.LINK_TEXT, 'id': By.ID, 'xpath': By.XPATH, 'class': By.CLASS_NAME, 'name': By.NAME}
        
        for i in range(20):
            if find_by in elemType:
                elem = self.driver.find_elements(elemType[find_by], element)
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
                        log.Logger('*** Error : Can not %s, with "%s" & "%s" & "plural=%s"' %(tmp, find_by, element, str(plural)), 'RED' , timestamp=0)
                        return False
                    time.sleep(1)
            # Ex
                # <div _ngcontent-byd-c40="" routerlink="health" routerlinkactive="active" class="row middle-xs menu unlocked" tabindex="0"><div _ngcontent-byd-c40="" icon="assets/icons/icon-health-check.svg" class="icon"><svg data-name="icons" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 19 23.67">
                # driver.find_element_by_xpath("//*[@routerlink='health']")
                # driver.find_element_by_xpath("//div[@routerlink='health']")
            ### Ex2
                # <label class="check-label" for="filter_net_redir">Filter Internet NAT Redirection</label>
                # elem = driver.find_elements(By.XPATH, "//div//label[@for='filter_net_redir']")
            elif find_by == 'url':
                try:
                    log.Logger('Selenium : Access "%s"'%element)
                    self.driver.get(element)
                    return True
                except:
                    log.Logger('Selenium : Can not access %s'%element)
                    return False

            elif find_by == 'alert':
                try:
                    text = Alert(self.driver).text
                    log.Logger( 'Selenium : Alert "%s"' %text)
                    time.sleep(1)
                    Alert(self.driver).accept()
                    return text
                except Exception as e:
                    log.Logger('Selenium : Alert "%s"' %str(e))
                    return False
            
            elif action == 'refresh':
                self.driver.refresh()
                time.sleep(3)
                return True

                    
        for i in range(25):
            try:
                if action == 'click':
                    elem.click()
                elif action == 'double_click':
                    ActionChains(self.driver).double_click(elem).perform()
                elif 'clear' in action : 
                    elem.clear()
                elif 'key' in action:
                    elem.clear()
                    if action[1] != '':
                        elem.send_keys(action[1])
                elif action == 'text':
                    return elem.text
                elif 'grep' in action:
                    get = elem.get_attribute(action[1])
                    if get == None:
                        log.Logger('Selenium : grep "None"')
                    else:
                        get = str(get)
                        log.Logger('Selenium : grep "%s"'%get)
                    return get 
                    ### 獲取沒有屬性的隱藏value
                    # elem.get_attribute('textContent')
                    # elem.get_attribute('innerHTML')
                    # elem.get_attribute('innerText')
                elif 'select' in action:
                    Select(elem).select_by_visible_text(action[1])
                elif action == 'switch':
                    self.driver.switch_to_window(self.driver.window_handles[element])
                elif action == 'is_enabled':
                    return elem.is_enabled()
                time.sleep(wait)
                return True
            except Exception as e:
                if i == 20:
                    log.Logger('*** Error : ' + str(e))
                    return False
                time.sleep(0.5)
    

    def grep_title_value(self, row_class, key_class, value_class, filter_Byxpath=''):
        if filter_Byxpath != '':
            rows = self.driver.find_element_by_xpath(filter_Byxpath).find_elements_by_class_name(row_class)
        else:
            rows = self.driver.find_elements_by_class_name(row_class)

        key_list = []
        value_list = []
        for row in rows:
            tmp_keys = row.find_elements_by_class_name(key_class)
            tmp_values = row.find_elements_by_class_name(value_class)
            if len(tmp_keys) > 0 and len(tmp_values) > 0:
                tmp_keys = tmp_keys[0]
                tmp_values = tmp_values[0]
                key_list.append(tmp_keys.get_attribute('innerText'))

                if 'toggle' in value_class:
                    handle = tmp_values.find_elements_by_class_name('checked')
                    if len(handle) > 0:
                        value_list.append('Enabled')
                    else:
                        value_list.append('Disabled')
                else:
                    handle = tmp_values.find_elements_by_class_name('marked')
                    if len(handle) > 0:
                        handle = handle[0]
                        value_list.append(handle.get_attribute('innerText'))
                    else:
                        value_list.append(tmp_values.get_attribute('innerText'))

        return dict(zip(key_list,value_list))

