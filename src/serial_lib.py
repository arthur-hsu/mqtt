import serial
import serial.tools.list_ports
import os, time, sys
from . import colorLog as log
import config.config as cf
import threading, queue




class Serial_Module:
    def __init__(self, port, baudrate, timeout=5, logname='', read_timeout=0.1):
        self.baudrate = baudrate
        self.port = port
        self.timeout = timeout
        self.cmd, self.expected, self.result = '', '' , ''
        self.logname = logname
        self.read_timeout = read_timeout
        self.w_encode = 1

    
    def parser(self):
        try:
            multi_ps_is_alive = self.multi_ps.is_alive()
        except:
            multi_ps_is_alive = False

        if multi_ps_is_alive:
            #log.Logger('multi uart_ps is alive.')
            return True
        else:
            for i in range(2):
                if Port_is_alive(self.port):
                    UART = self.Connect()
                    break
                elif i == 1:
                    log.Logger('No ' + self.port, fore='RED' , logname=self.logname)
                    return False
                else:
                    time.sleep(3)
            if UART:
                self.multi_ps= threading.Thread(target = self.Read)
                self.multi_ps.daemon = True
                self.multi_ps.start()
                time.sleep(self.read_timeout+0.1)
                return True
            else:
                return False

    def get_port(self):
        return self.port


    def Read(self):
        self.stop = 0
        while self.stop == 0 :
            if self.cmd != '':
                log.Logger('%s : %s' %(self.port, self.cmd), 'BLACK', 'WHITE', logname=self.logname)
                '''while len(self.cmd) >= 100:
                    self.DutSer.write(str.encode(self.cmd[0:100]))
                    self.cmd = self.cmd[100:]
                    time.sleep(0.1)'''
                self.cmd = str.encode(self.cmd + '\r') if self.w_encode == 1 else self.cmd 
                self.DutSer.write(self.cmd)
                self.cmd = ''
            try:
                line = self.DutSer.readline()
                line = line.decode('ascii').replace('\n', '').replace('\r', '')
            except Exception as e:
                read_fail = ['readiness to read but returned no data', 'read failed']
                decode_fail = ['decode']
                if any(string in str(e) for string in read_fail): 
                    self.DutSer.close()
                    log.Logger(str(e), fore='RED')
                    log.Logger('\t\tDisconnected with Port %s...' %self.port, 'RED', timestamp=0)
                    Boot_time_start = time.time()
                    log.Logger('\t\tWait Booting...', timestamp=0)
                    time.sleep(1)
                    for i in range(600):
                        time.sleep(0.1)
                        if Port_is_alive(self.port):
                            log.Logger('\t\tBoot finished %s sec' %round(time.time() - Boot_time_start,1), timestamp=0)
                            self.Connect()
                            '''tsmode = ['ATC+TSMODE=1', 'ATC+DEBUG=1']
                            for test in tsmode:
                                log.Logger('%s : %s' %(self.port, test), 'BLACK', 'WHITE', logname=self.logname)
                                self.DutSer.write(str.encode('%s\r'%test))
                                time.sleep(0.5)'''
                            break
                        elif i == 599:
                            log.Logger('Failed to open ' + self.port, fore='RED' , logname=self.logname)
                            return False

                elif any(string in str(e) for string in decode_fail): 
                    log.Logger("%s, \n%s\n\n Ignore the can't decode byte." %(str(e), line), fore = 'RED', timestamp=0)
                    log.Logger('%s : %s' %(self.port, line.decode('ascii', 'ignore').replace('\n', '').replace('\r', '')), 'RED')
                else:
                    Logger('%s\n\tNo definition error'%str(e), fore = 'RED', timestamp=0)
                line = '' 

            if self.expected != '' and self.cmd == '':
                self.dumpMeg += line if line =='' else '%s\n' %line
                if any(string in line for string in self.expected) and ('?' not in line): 
                    log.Logger('%s : %s' %(self.port, line), 'GREEN', logname=self.logname)
                    self.result = line
                    line = ''
                elif (time.time() - self.time_start) > self.timeout:
                    self.result = False
            if line != '':
                fore = 'None'
                log.Logger('%s : %s' %(self.port, line), fore= fore if not any(string in line for string in cf.get_value('err')) else 'MAGENTA', logname=self.logname)
        self.DutSer.close()

    

    def send_result(self):
        try:
            self.task.join()
            self.timeout = self.orig_timeout
            self.w_encode = 1
            return self.que.get(timeout = self.timeout)
        except:
            log.Logger('\tMulti_send is not started.', fore='GREEN', timestamp=0)
            return False


    def write(self, cmd, expected='', makeTrue=0, dump_duration=0, encode=1):
        if not expected == '':
            if type(expected) == type('string'):
                expected = [expected]
            if 'NONE' in [s.upper() for s in expected if isinstance(s, str)==True]:
                expected = ''

        if dump_duration > 0:
            orig_timeout = self.timeout
            self.timeout = dump_duration
            expected = ['dumpAll'] if expected == '' else expected

        self.w_encode = encode

        retry = 0
        while True:
            try:
                multi_ps_is_alive = self.multi_ps.is_alive()
            except:
                multi_ps_is_alive = False
            if not multi_ps_is_alive:
                if not self.parser():
                    return False
            self.dumpMeg, self.result = '', ''
            self.cmd = cmd
            self.expected = expected
            if self.expected != '':
                self.time_start = time.time()
                while self.result == '':
                    time.sleep(self.read_timeout)
                if self.result == False and self.expected != ['dumpAll'] :
                    log.Logger('\t\t\t\t%s is not found' %self.expected, fore='RED', timestamp=0 , logname=self.logname)
                self.expected = ''
                if self.result or makeTrue==0 or retry >= makeTrue:
                    if dump_duration > 0:
                        self.timeout = orig_timeout
                        return self.dumpMeg
                    else:
                        return self.result
                if makeTrue > 1:
                    retry += 1
            else:
                time.sleep(0.5)
                return True



    def Connect(self):
        try:
            self.DutSer = serial.Serial(self.port, int(self.baudrate), timeout=self.read_timeout)
            return True
        except Exception as e:
            log.Logger(str(e), fore='RED')
            log.Logger('Failed to open ' + self.port, fore='RED' , logname=self.logname)
            return False
    



    def Close(self):
        self.stop = 1
        try:
            self.multi_ps.join()
        except:
            None

    
    def set_timeout(self, timeout=''):
        if timeout=='' :
            return self.timeout
        else:
            self.timeout = int(timeout)

    def set_read_timeout(self, timeout):
        self.read_timeout = timeout
        log.Logger('\tSwitch the "flush time" to %s sec' %(timeout), 'GREEN', timestamp=0)
        self.Close()
        self.parser()
    


def Port_is_alive(port):
    if serial.tools.list_ports.comports() != []:
        port_list = []
        for _port in list(serial.tools.list_ports.comports()):
            port_list.append(_port[0])
        #port_list.sort()
        #print(port_list)
        if port in port_list:
            time.sleep(0.1)
            return True
    return False
