import time
import pexpect
import subprocess
import sys, re, os, threading
from . import colorLog as log
import config.config as cf
import src.commonFunction as commonFunction

fun = commonFunction.Common()

class Bluetoothctl:
    def __init__(self, intervace='hci0', slave='', timeout=5, logname='', read_timeout=0.1):
        out = subprocess.check_output("rfkill unblock bluetooth", shell = True)
        self.intervace = intervace
        self.child = pexpect.spawn("bluetoothctl", echo = False)
        self.timeout = timeout
        self.expected, self.result = '', ''
        self.logname = logname
        self.parsing = 0
        self.slave = slave
        self.read_timeout = read_timeout


    def get_output(self, command, expected=['#', pexpect.EOF], timeout = 1, pause=0.05, shell=True):
        if 'write' in command:
            txdata = bytes.fromhex(command.replace('gatt.write "', ' ').replace(' 0x', '').replace('"','')).decode('ascii').replace('\r\n','')
            log.Logger('ble.Tx : %s'%txdata, 'BLACK', 'WHITE')
        else:
            log.Logger(command, 'BLACK', 'WHITE')
        if self.child.before:   
            self.child.expect(r'.+')
        self.child.sendline(command)
        res = False
        dump=''
        try:
            time.sleep(pause)
            self.child.expect(expected, timeout=timeout)
            res = True
        except :
            None
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
        for line in self.child.before.decode('ascii', 'ignore').split('\r\n'):
            if shell == True and line != '' and '[DEL]' not in line:
                log.Logger(line, timestamp=0)
                dump += '%s\n'%(ansi_escape.sub('', line).replace('\x01\x02', ''))
        if not res:
            log.Logger("\tFailed to %s"%command, fore='RED', timestamp=0)
        return dump if res == True else False



    def scan(self, mac_address='', duration=5):
        mac_address = self.slave if mac_address == '' else mac_address
        '''command = ['hciconfig $i down', 
                  'hciconfig $i up', 
                  'timeout -s SIGINT %s hcitool -i $i lescan'%duration]
        for cmd in command:
            log.Logger(cmd.replace('$i', self.intervace), timestamp=0)
            scan_ps = os.popen(cmd.replace('$i', self.intervace))
            time.sleep(0.5)'''
        devices_data = ''
        grep_dev = False
        time_start = time.time()
        while time.time() - time_start < duration and grep_dev==False:
            scan_ps = os.popen('timeout -s SIGINT 1s hcitool -i %s lescan'%self.intervace)
            while True:
                line = scan_ps.buffer.readline().decode('ascii', 'ignore')
                line = line.strip(' ').replace('\n','').upper()
                if line != '' :
                    #log.Logger(line, timestamp=0)
                    devices_data += ' %s' %line
                if mac_address !='' and mac_address.upper() in line:
                    mac_address = self.grab_device_mac(mac_address, devices_data)
                    grep_dev = True
                    break
        scan_ps.close()

        while time.time() - time_start < duration:
            self.get_output("scan on", shell=True)
            time.sleep(0.5)
            scan_dev = self.get_output("scan off", ['Discovery stopped'], timeout=3, shell=True)
            if scan_dev and mac_address in scan_dev.upper():
                return mac_address
        log.Logger('\tScan %s, Failed'%mac_address, fore='RED', timestamp=0)
        return False

    
    def grab_device_mac(self, dev, devices_data):
        if not dev.count(':') == 5 :
            dev_list = devices_data.replace('\n',' ').split(' ')
            try:
                mac_address = dev_list[dev_list.index(dev)-1]
            except Exception as e:
                log.Logger(str(e), 'RED', timestamp=0)
                mac_address = False
        else:
            mac_address = dev
        return mac_address


    def connect(self, mac_address=''):
        mac_address = self.slave if mac_address == '' else mac_address
        self.connection = 0
        mac_address = mac_address.upper()
        paired_devices = self.get_output(command='paired-devices', pause=1).upper()
        if mac_address not in paired_devices:
            mac_address = self.scan(mac_address, 30)
        else:
            mac_address = self.grab_device_mac(mac_address, paired_devices)
        if not mac_address:
            return False
        self.get_output(command="scan off", shell=False)
        for i in range(5):
            if mac_address in paired_devices:
                res = self.get_output("connect " + mac_address, ['ServicesResolved: yes', 'Connection successful'], 5)
            else:
                res = self.get_output("pair %s"%mac_address, ["Pairing successful"], 5)
            if res:
                self.connection = 1
                self.parser()
                self.notify()
                log.Logger('\tConnection successful', 'GREEN', timestamp=0)
                return True
        self.Close()
        return False
    
    def conn_status(self):
        return True if self.connection==1 else False


    def notify(self, tx_uuid='6e400003-b5a3-f393-e0a9-e50e24dcca9e', rx_uuid='6e400002-b5a3-f393-e0a9-e50e24dcca9e'):
        self.get_output("gatt.select-attribute %s"%tx_uuid)
        res = self.get_output("gatt.notify on", ['Notify started', 'NotSupported'], timeout=5)
        self.get_output(command="gatt.select-attribute %s"%rx_uuid)




    def remove(self, mac_address=''):
        mac_address = self.slave if mac_address == '' else mac_address
        paired_devices = self.get_output(command='paired-devices', pause=1).upper()
        mac_address = self.grab_device_mac(mac_address.upper(), paired_devices)
        res = self.get_output("disconnect " + mac_address, ["Connected: no"], 5)
        rese = self.get_output("remove " + mac_address, ['Device has been removed'], 5)
        return True if res else False



    def disconnect(self, mac_address=''):
        mac_address = self.slave if mac_address == '' else mac_address
        paired_devices = self.get_output(command='paired-devices', pause=1).upper()
        mac_address = self.grab_device_mac(mac_address.upper(), paired_devices)
        res = self.get_output("disconnect " + mac_address, ["Connected: no"], 5)
        return True if res else False
    


    def write(self, cmd, expected='', makeTrue=0, dump_duration=0):
        if not expected == '':
            if type(expected) == type('string'):
                expected = [expected]
            if 'NONE' in [s.upper() for s in expected if isinstance(s, str)==True]:
                expected = ''
        if dump_duration > 0:
            orig_timeout = self.timeout
            self.timeout = dump_duration
            expected = ['dumpAll'] if expected == '' else expected

        cmd = cmd.encode('ascii').hex() + '0d0a'
        pattern = re.compile('.{2}')
        cmd = '0x' + ' 0x'.join(pattern.findall(cmd))

        retry = 0
        while True:
            if self.connection != 1:
                log.Logger("\tNo Connection", fore='RED', timestamp=0)
                return False
            self.dumpMeg, self.result = '', ''
            self.expected = expected
            if not int(fun.shell("ps aux | grep 'sudo hcidump'| grep -v grep -c",'',False)) > 0:
                self.parser()
            if cmd != '0x0d 0x0a':
                res = self.get_output(command='gatt.write "%s"'%cmd, timeout=1, pause=0, shell=False)
            time_start = time.time()
            if self.expected != '':
                while (time.time() - time_start) <= self.timeout and self.result == '':
                    time.sleep(self.read_timeout)
                self.expected = ''
                self.result = False if self.result == '' else self.result
                if self.result == False and self.expected != ['dumpAll'] :
                    #killProcess('sudo hcidump')
                    log.Logger('\t\t\t\t%s is not found' %expected, fore='RED', timestamp=0 , logname=self.logname)
                if self.result or makeTrue==0 or retry >= makeTrue:
                    if dump_duration > 0:
                        self.timeout = orig_timeout
                        return self.dumpMeg
                    else:
                        return self.result
                if makeTrue > 1:
                    retry += 1
            else:
                return True
        
        

    def set_timeout(self, timeout=''):
        if timeout=='' :
            return self.timeout
        else:
            self.timeout = int(timeout)




    @log.multi_thread
    def parser(self):
        self.parsing = 1
        p = os.popen('sudo hcidump -i %s'%self.intervace)
        while self.parsing == 1 :
            try:
                line = p.buffer.readline().decode('ascii', 'ignore').strip(' ')
                if 'Handle notify' in line:
                    ble_rx = True
                elif 'Write req' in line:
                    ble_rx = False
                elif 'HCI Event: Disconn Complete' in line:
                    log.Logger("\tDisconnected with devices.", fore='RED', timestamp=0)
                    self.parsing = 0
                    self.connection = 0
                line = bytes.fromhex(line.split('value')[-1].replace(' 0x', '')).decode('ascii').replace('\r\n','') if 'value' in line and ble_rx else ''
                '''if all(string in line for string in ['OK', 'ATC+']):
                    index = line.find('OK')
                    line = line[:index] + '\n' + line[index:]'''
            except Exception as e:
                log.Logger(str(e), fore='RED', timestamp=0)
                line = ''
            if self.expected != '' :
                self.dumpMeg += line if line =='' else '%s\n' %line
                if any(string in line for string in self.expected) and ('?' not in line): 
                    log.Logger('%s : %s' %('ble_Rx', line), 'GREEN', logname=self.logname)
                    self.result = line
                    line = ''
            if line != '':
                fore = 'None'
                log.Logger('%s : %s' %('ble.Rx', line), fore= fore if not any(string in line for string in cf.get_value('err')) else 'MAGENTA', logname=self.logname)
        self.Close()
        p.close()
                    


    def Close(self):
        #log.Logger('\tKill the parser of hcidump.', timestamp=0)
        self.parsing = 0
        killProcess('sudo hcidump')



def killProcess(keyword):
    command = os.popen('ps aux | grep "' + keyword + '"')
    def string_to_list_remove_empty(string, handle):
        string = string.strip(' ').split(handle)
        string = list(filter(None, string))
        return string

    while True:
        tmp = command.buffer.readline().decode('ascii', 'ignore')
        items = string_to_list_remove_empty(tmp, ' ')
        if tmp == '':
            break
        elif (len(items) > 3) and ('mount' not in tmp) and ('grep' not in tmp) and ('Studio' not in tmp) and ('/Applications/Vysor.app/Contents/Frameworks/Vysor' not in tmp) :
            subprocess.call(["kill", items[1]])
