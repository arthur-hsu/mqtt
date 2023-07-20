import src.colorLog as log
import allure
import time
import re




@allure.step("BLE Scanner over RAK_Board")
def BLE_Scanner(serial, mac_address):
    serial.parser()
    serial.set_timeout(10)
    result = serial.write('Search %s' %mac_address, mac_address)
    return result
