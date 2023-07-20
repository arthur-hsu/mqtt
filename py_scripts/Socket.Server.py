
#! python3
from asyncio import protocols
import datetime
from sys import argv
import time, re
import socket
import threading
import traceback
import subprocess
import os
import platform
import locale
import math, random, queue
from http.server import HTTPServer, SimpleHTTPRequestHandler
import telnetlib






def recvdata(clientSock):
  s = clientSock
  while True:
    try:
      data = s.recv(BUFSIZ).decode()
      ToClient = "[From Remote] : Success."
      if len(data) != 0:
        unit_dict = {'T': [0.1, '°C', "0[1-9]67([^?]\w\w\w)"], \
                     'H': [0.1, '%', "0[1-9]68([^?]\w\w\w)"], \
                     'P': [0.1, 'hPA', "0[1-9]73([^?]\w\w\w)"], \
                     'A': [0.001, 'G', "0[1-9]71([^?]\w\w\w\w\w\w\w\w\w\w\w)"], \
                     'pH': [0.1, '', "0[1-9]c2([^?]\w\w\w)"], \
                     'WS': [0.01, 'm/s', "0[1-9]be([^?]\w\w\w)"], \
                     'WD': [1, '°', "0[1-9]bf([^?]\w\w\w)"], \
                     #'Analog Input (Current)': [0.01, 'mA', "0[1-9]02([^?]\w\w\w)"], \
                     'Pyranometer': [1, 'W/m2', "0[1-9]c3([^?]\w\w\w)"], \
                     'EC': [0.001, 'mS/cm', "0[1-9]c0([^?]\w\w\w)"]}
        value = ''
        for sensor_type in unit_dict.keys():
            _value = re.findall(unit_dict[sensor_type][2], data)
            if len(_value)>0:
                for i in _value:
                    unit = unit_dict[sensor_type]
                    if sensor_type == 'A':
                        value += 'XYZ: %s%s, %s%s, %s%s, '   %(round(twosComplement_hex(i[0:4])*unit[0],2), unit[1],\
                                                               round(twosComplement_hex(i[4:8])*unit[0],2), unit[1],\
                                                               round(twosComplement_hex(i[8:12])*unit[0],2), unit[1])
                    else:
                        value += '%s: %s%s, '   %(sensor_type, round(twosComplement_hex(i)*unit[0],2), unit[1])
        if len(value) > 0 :
            data += '\n\t\t\t\t\t\t\t\t  %s' %(value[0:-2])
        Logger("[-] Client " + str(s.getpeername()) + " : %s" % data)

        if 'cmd' in data[0:3]:
            ToClient = parseCmd(data)

        elif 'kill' in data:
            process_killed = data.replace('kill ', '')
            killProcess(process_killed)
            ToClient = '[From Remote] : killed %s'%process_killed
        
        elif 'telnet' in data:
            telnet_dict = eval(str(data))
            ToClient = telnet_cmds(telnet_dict['telnet']['ip'], telnet_dict['telnet']['cmd'] )
        
        elif 'socket' in data:
            socket_dict = eval(str(data))
            ToClient = socket_cmd(socket_dict['socket']['ip'], socket_dict['socket']['protocol'], socket_dict['socket']['cmd'] )

        elif 'iperf' in data:
          if 'divider' in data:
              dataSplit = data.split(' ')
              port = int(dataSplit[dataSplit.index('-p')+1])
              divider = int(dataSplit[dataSplit.index('divider')+1])
              dataSplit.pop(dataSplit.index('-p')+1)
              dataSplit.pop(dataSplit.index('-p'))
              dataSplit.pop(dataSplit.index('divider')+1)
              dataSplit.pop(dataSplit.index('divider'))
              cmd = ' '.join(dataSplit)
              Logger('iperf cmd : %s' %cmd)
              names = locals()
              for i in range(divider):
                  names[ 'que%s' % str(i)] = ''
                  names[ 'que%s' % str(i)] = queue.Queue()
                  names[ 'iperf_pair%s' % str(i)] = threading.Thread(target=lambda q, arg1: names['que%s' % str(i)].put(parse_Iperf(arg1)), args=( names['que%s' % str(i)], cmd + ' -p ' + str(port+i) ))
                  names[ 'iperf_pair%s' % str(i)].daemon = True
                  names[ 'iperf_pair%s' % str(i)].start()
                  time.sleep(0.2)
              for i in range(divider):
                  names[ 'iperf_pair%s' % str(i)].join()
              ToClient = "[From Remote] : \n"
              for i in range(divider):
                  ToClient = ToClient + names[ 'que%s' % str(i)].get() + ',\n'
          else:
              ToClient = "[From Remote] : %s" %parse_Iperf(data)


      if (data == "quit") or (len(data) == 0):
        Logger("[-] " + str(s.getpeername()) + ": Disconnected.")
        end = str(s.getpeername())
        s.close()
        break
      elif data == '-=BEGIN=-67890qwertyuiop!@#$%^&*()1234567890asdfghjkl!@#$%^&*()1234567890zxcvbnm,./4546474849505152535451234567890qwertyuiop!@#$%^&*()1234567890asdfghjkl!@#$%^&*()1234567890zxcvbnm,./4546474849505152535451234567890qwertyuiop!@#$%^&*()90asdfghjkl!@#$-=END=-':
        ToClient = "-=BEGIN=-67890qwertyuiop!@#$%^&*()1234567890asdfghjkl!@#$%^&*()1234567890zxcvbnm,./4546474849505152535451234567890qwertyuiop!@#$%^&*()1234567890asdfghjkl!@#$%^&*()1234567890zxcvbnm,./4546474849505152535451234567890qwertyuiop!@#$%^&*()90asdfghjkl!@#$-=END=-"
        s.sendall(ToClient.encode())

      else:
        if ToClient :
          pass
        elif ToClient == None:
          ToClient = "[From Remote] : command not found."
        else:
          ToClient = "[From Remote] : Success."
        s.sendall(ToClient.encode())

    except Exception as e:
      Logger(str(e))
      if '強制關閉' in str(e) or 'connection abort' in str(e) or '中止' in str(e) or '[Errno 22]' in str(e):
          s.close()
          return None
      time.sleep(0.1)

def twosComplement_hex(hexval):
    bits = 16
    val = int(hexval, bits)
    if val & (1 << (bits-1)):
        val -= 1 << bits
    return val



def parse_Iperf(strings):
      midsplit = str(strings).split(' ')
      ToClient = '0 Mbits/sec'
      if (len(midsplit) >= 1) and ('iperf' in midsplit[0]):
          command = os.popen(strings)
          Logger("\n")
          while True:
              tmp = command.buffer.readline().decode(locale.getdefaultlocale()[1], 'ignore')
              if (tmp == '') or ('iperf Done' in tmp) or ('WARNING' in tmp) or (('connected with' in tmp) and (ToClient != '0 Mbits/sec')):
                  break
              elif '-p' in midsplit:
                 tmp = ' port %s : %s' %(midsplit[midsplit.index('-p')+1], tmp)
              tmp = tmp.replace('\n','')
              Logger(tmp)
              ### iperf3
              if 'receiver' in tmp :
                  ToClient = tmp
              
              ### iperf2
              elif (' 0.00-' in tmp) and ('0.00-1.00' not in tmp) and ('out-of-order' not in tmp):
                  ToClient = tmp

      return ToClient





def parseCmd(strings):
  midsplit = str(strings).split(" ")
  ToClient = ''
  if (len(midsplit) >= 2) and (midsplit[0] == "cmd"):
    command = os.popen(strings.replace('cmd ', ''))
    Logger("\n")
    while True:
      tmp = command.buffer.readline().decode(locale.getdefaultlocale()[1], 'ignore')
      if (tmp == '') :
        break
      else:
        ToClient += tmp
        Logger(tmp.replace('\n',''))

  if ToClient == '':
    ToClient = None
  return ToClient


def socket_cmd(ip, protocol, cmd, port=9580):
    Logger("[+] Send %s to %s" %(protocol,ip ))
    if protocol == 'TCP':
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # socket.SOCK_STREAM, socket.SOCK_DGRAM
        s.settimeout(1)
        try:
            s.connect((ip, port))
            s.sendall(cmd.encode())
            bResult = 'True'
        except Exception as e:
            Logger(str(e))
            return 'False'

    elif protocol == 'UDP':
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # socket.SOCK_STREAM, socket.SOCK_DGRAM
        s.settimeout(1)
        try:
            s.sendto(cmd.encode(), (ip, port))
            recvdata = s.recv(4096)
            bResult = 'True'
        except Exception as e :
            Logger(str(e))
            return 'False'

    s.close()

    return bResult


def telnet_cmds(ip, cmds):
    try:
        tn = telnetlib.Telnet(ip, timeout=1)
        bResult = '[From Remote] : Telnet Finished.'
    except:
        Logger('Can not telnet %s, Failed.' %ip)
        return '[From Remote] : Can not telnet %s, , Failed.' %ip
    for cmd in cmds:
        tn.write(cmd.encode('ascii') + b"\n")
        while True:
            line = tn.read_until(b"\n", timeout=0.3)  # Read one line
            line = str(line, encodeType).replace('\r\n', '')
            Logger('Telnet : %s' %line)
            if ":/#" in line and cmd not in line:  # last line, no more read
                break
    tn.close()
    Logger('*** Telnet Done.')
    return bResult




def Logger(log):
    log = str(log)
    f = open(initlogpath + logFile + '.txt', 'a')
    print('\n[%s]  %s' %(time.ctime(), log), file = f)
    f.close()
    print('\n[%s]  %s' %(time.ctime(), log))


def killProcess(keyword):
        if 'Windows' in platform.system():
        ### Find the PID with port.
            if '-p' in keyword:
                handle = string_to_list_remove_empty(keyword, ' ')
                command = os.popen('netstat -ano | findstr ' + handle[handle.index('-p') + 1])
                port_PID = command.buffer.readline().decode(locale.getdefaultlocale()[1], 'ignore')
        ### Find the PID with name.
                command = os.popen('tasklist | find "' + handle[0] + '.exe"')
                tmp = command.buffer.readline().decode(locale.getdefaultlocale()[1], 'ignore')
                name_PID = string_to_list_remove_empty(tmp, ' ')
                if name_PID[1] in port_PID:
                    Logger(name_PID)
                    command = os.popen('taskkill /PID ' + name_PID[1] + ' /F')
                else:
                    Logger('Can not find ' + keyword + ' and port ' + handle[handle.index('-p') + 1])
            else:
                command = os.popen('Taskkill /F /IM ' + keyword + '.exe')
        else:
            command = os.popen('ps aux | grep "' + keyword + '"')
            while True:
                tmp = command.buffer.readline().decode(locale.getdefaultlocale()[1], 'ignore')
                items = string_to_list_remove_empty(tmp, ' ')
                if tmp == '':
                    break
                elif (len(items) > 3) and  ('grep' not in items) and ('Studio' not in items) and ('/Applications/Vysor.app/Contents/Frameworks/Vysor' not in items) :
                    Logger(tmp.replace('\n', ''))
                    Logger("kill {0}...".format(items[1], subprocess.call(["kill", items[1]])))
    


def string_to_list_remove_empty(string, handle):
    string = string.split(handle)
### remove empty from list
    string = list(filter(None, string))
    return string



def tcp_Services():
  while True:
    clientSock, addr = tcpSerSock.accept()
    Logger("[+] Connect success -> at " + str(addr) )

    ### 如果1個ser服務多個client, 需要設為non blocking mode
    ### 現在用多線程, 替每位client生成一個ser, 所以不需要
    #clientSock.setblocking(0)

    t = threading.Thread(target=recvdata, args=(clientSock, ))
    t.daemon = True
    t.start()

def udp_Service():
    while True:
        indata, addr = udpSerSock.recvfrom(1024)
        Logger('UDP Data %s : ' %(str(addr), indata.decode()))

        outdata = 'Echo ' + indata.decode()
        udpSerSock.sendto(outdata.encode(), addr)



def http_server():
    http_port = 8080
    Logger("[+] Starting Http server on port %s" %http_port)
    server = HTTPServer(('', http_port), SimpleHTTPRequestHandler)
    server.serve_forever()






if __name__ == "__main__":

  encodeType = locale.getdefaultlocale()[1]
  logFile = time.strftime( "%Y.%m.%d_%X", time.localtime() )
  logFile = logFile.replace(":", "")
  initlogpath = os.path.abspath(os.path.dirname(__file__)) + '/_log/'
  if not os.path.exists(initlogpath):
      os.makedirs(initlogpath)
    

  http_process = threading.Thread(target=http_server)
  http_process.daemon = True
  http_process.start()

  PORT = 7000
  BUFSIZ = 1024
  ADDR = ('', PORT)
  Logger("[+] Starting TCP & UDP Socket server on port %s" %(PORT) )

  tcpSerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  #TCP Socket
  tcpSerSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  tcpSerSock.bind(ADDR)
  tcpSerSock.listen(5)

  udpSerSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  #UDP Socket
  udpSerSock.bind(ADDR)

  tcpProcess = threading.Thread(target=tcp_Services)
  tcpProcess.daemon = True
  tcpProcess.start()

  udpProcess = threading.Thread(target=udp_Service)
  udpProcess.daemon = True
  udpProcess.start()

  while True:
    input()




