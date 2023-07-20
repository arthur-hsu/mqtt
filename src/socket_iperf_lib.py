import socket
import serial
import serial.tools.list_ports
import src.colorLog as log
import os, platform, subprocess, queue, math, time
import threading
import locale
operation_system = platform.system()
encodeType = locale.getdefaultlocale()[1]







class Socket_Module:
    def __init__(self):
        self.socket_client_list = []

    def Connection(self, ip, port=9580):
        try:
            log.Logger('Connect to Remote ' + ip , 'GREEN')
            sock_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_conn.connect((ip, port))
            time.sleep(1)
            self.socket_client_list.append(sock_conn)
            return sock_conn
        except:
            log.Logger('Can not Remote ' + ip , 'RED')
            return False
    
    def Send(self, client, data, timeout=3):
        conn = client
        if not isinstance(conn,type(socket.socket(socket.AF_INET, socket.SOCK_STREAM))):
            conn = self.Connection(conn)
        recvdata = False
        if conn:
            conn.settimeout(timeout)
            try:
                log.Logger('[To Remote ' + conn.getpeername()[0] + '] : ' + data, 'YELLOW')
                conn.sendall(data.encode())
                recvdata = conn.recv(4096)
                if recvdata:
                    recvdata = recvdata.decode()
                    log.Logger( '[From Remote ' + conn.getpeername()[0] + '] : ' + str(recvdata), 'GREEN' )
            except Exception as e:
                log.Logger('Exception : ' + str(e))
                log.Logger('*** Socket Sent, failed', 'RED')
        return recvdata
    

    
    def Disconnection(self, client=''):
        if client != '':
            try:
                client.close()
                return
            except:
                None
        else:
            for item in self.socket_client_list:
                try:
                    item.close()
                except:
                    None
            self.socket_client_list = []

    def MAC_Grep(self, ip, port):
        conn = self.Connection(ip, port)
        print('[To Remote PC] : netsh wlan show interfaces')
        recvdata = self.Send(conn, 'cmd netsh wlan show interfaces')
        if recvdata:
            recvdata = recvdata.replace(' ', '').replace('\r','').replace('實體位址', 'Physicaladdress').split('\n')
            recvdata = list(filter(None, recvdata))
            wifi_dict = {}
            for i in range(len(recvdata)):
                try:
                    wifi_dict.setdefault(recvdata[i].split(':')[0], recvdata[i].replace(recvdata[i].split(':')[0]+':',''))
                except:
                    None
            conn.close()
            if 'Physicaladdress' in wifi_dict:
                return wifi_dict['Physicaladdress']
            else:
                return None
        else:
            return None


    def Rate_RSSI_Socket(self, delaytime, client):
        time.sleep(delaytime)
        print('[To Remote PC] : netsh wlan show interfaces')
        wifi_dict = {'TXRATE':'0', 'RXRATE':'0', '訊號':'0%', 'Physicaladdress': None}
        recvdata = self.Send(client, 'cmd netsh wlan show interfaces', 3)
        if recvdata:
            recvdata = recvdata.replace(' ', '').replace('\r','').replace('傳輸速率(Mbps)', 'TXRATE').replace('接收速率(Mbps)', 'RXRATE').replace('實體位址', 'Physicaladdress').split('\n')
            recvdata = list(filter(None, recvdata))
            handle = {}
            for i in range(len(recvdata)):
                try:
                    handle.setdefault(recvdata[i].split(':')[0], recvdata[i].replace(recvdata[i].split(':')[0]+':',''))
                except:
                    None
            #log.Logger(str(wifi_dict))
            if 'TXRATE' in handle and 'RXRATE' in handle:
                wifi_dict = handle
        return wifi_dict
        

    def Rate_RSSI_QCA(self, dutip, delaytime, mac_addr):
        interface = ''
        tmp = ''
        try:
            tn = telnetlib.Telnet(dutip, timeout=0.3)
            tmp = tn.read_until(b"OpenWrt", timeout=0.3)
            cmd = "ls ini/ | grep QC"
            tn.write(cmd.encode('ascii') + b"\n")
            tmp = tn.read_until(b"OpenWrt", timeout=0.3)
            interface = 'telnet'
            log.Logger('Grep Rate & RSSI from telnet.')
        except:
            log.Logger('Can not access telent, try console...')
        if interface == '' and serial.tools.list_ports.comports() != []:
            port_list = []
            for port in list(serial.tools.list_ports.comports()):
                port_list.append(port[0])
            try:
                DutSer = serial.Serial(port_list[0], 115200, timeout = 0.5 )
                DutSer.write(("ls ini/ | grep QC\r").encode())
                tmp = DutSer.readlines()
                interface = 'console'
                log.Logger('Grep Rate & RSSI from ' + port_list[0])
            except:
                log.Logger('Can not access console.')
                return False

        ## 判斷是否為QCA solution
        if len(tmp) <= 2:
            return False
        else:
            time.sleep(delaytime)
        try:
            for i in range(3):
                if interface == 'console':
                    DutSer.write(("wlanconfig ath" + str(i) + " list | grep -B1 " + mac_addr + "\r").encode())
                    tmp = DutSer.readlines()
                    if len(tmp) >= 4:
                        athx = i
                        ### tmp[0]是input
                        key = str(tmp[1], encodeType).replace('\r\n', '').split(' ')
                        value = str(tmp[2], encodeType).replace('\r\n', '').split(' ')
                        break
                elif interface == 'telnet':
                    cmd = "wlanconfig ath" + str(i) + " list | grep -B1 " + mac_addr
                    tn.write(cmd.encode('ascii') + b"\n")
                    tmp = tn.read_until(b"OpenWrt", timeout=0.3)
                    tmp = str(tmp, encodeType).split('\r\n')
                    if len(tmp) >= 4:
                        athx = i
                        key = tmp[1].split(' ')
                        value = tmp[2].split(' ')
                        break

            value = list(filter(None, value))
            key = list(filter(None, key))
            wlanconfig = dict(zip(key, value))
        
            if interface == 'console':
                DutSer.write(("wifistats wifi" + str(athx) + " 0 10\r").encode())
                time.sleep(0.3)
                DutSer.write(("wifistats wifi" + str(athx) + " 10 | grep per_chain_rssi_in\r").encode())
                tmp = DutSer.readlines()
                chain_list = []
                for i in tmp:
                    i = str(i, encodeType).replace(' ', '').replace('\r\n', '')
                    chain_list.append(i)
                DutSer.close()
            elif interface == 'telnet':
                cmd = "wifistats wifi" + str(athx) + " 0 10"
                tn.write(cmd.encode('ascii') + b"\n")
                tmp = tn.read_until(b"OpenWrt", timeout=0.3)
                cmd = "wifistats wifi" + str(athx) + " 10 | grep per_chain_rssi_in"
                tn.write(cmd.encode('ascii') + b"\n")
                tmp = tn.read_until(b"OpenWrt", timeout=0.3)
                chain_list = str(tmp, encodeType).replace(' ', '').split('\r\n')
                tn.close()
            rssi = {}
            for i in chain_list:
                if 'dbm' in i and '-128' not in i and '0:0,1:0,2:0,3:0' not in i:
                    value = i.split('=')
                    rssi['dbm ' + list(filter(str.isdigit, value[0]))[0]] = value[1]
            
            if 'TXRATE' in wlanconfig and 'RXRATE' in wlanconfig:
                return wlanconfig, rssi
            else:
                return False
        except:
            return False

    def Remote_Wireless_Connect(self, sock_ser_ip, ssid='', keyType='', cipherType='', password='', nonBroadcast = 'no', to_connect=1):
        for i in range(15):
            sock_conn = self.Connection(sock_ser_ip, 9580)
            if sock_conn :
                break
            else:
                log.Logger('Can not access socket ' + sock_ser_ip)
                time.sleep(3)
                if i%10 == 0:
                    return 'socketFail'
        
        receive = False
        if to_connect == 1:
            profile = "{'ssid':'" + ssid + "', 'keyType':'" + keyType + "', 'cipherType':'" + cipherType + "', 'password':'" + password + "', 'nonBroadcast':'" + nonBroadcast + "'}"
            receive = self.Send(sock_conn, profile, 300)
            if receive != False:
                receive = eval(str(receive))
        else:
            receive = self.Send(sock_conn, 'cmd netsh wlan disconnect', 3)
        self.Disconnection(sock_conn)
        return receive
    

    def Remote_Telnet_Cmd(self, sock_ser_ip, telnet_ip, cmd):
        for i in range(15):
            sock_conn = self.Connection(sock_ser_ip, 9580)
            if sock_conn :
                break
            else:
                log.Logger('Can not access socket ' + sock_ser_ip)
                time.sleep(3)
                if i%10 == 0:
                    return 'socketFail'
        ###   {'telnet': {'ip': '192.168.1.1', 'cmd': ['cmd1', 'cmd2', 'cmd3']}}
        cmd = {'telnet': {'ip': telnet_ip, 'cmd': cmd}}
        receive = self.Send(sock_conn, cmd, 300)
        self.Disconnection(sock_conn)
        return receive







class Iperf_Module:
    def __init__(self):
        self.socket = Socket_Module()

    def iperf2(self, direction, localIP, remoteIP, pairs, duration_time, udpbandwidth='500M', udplength='1460', expected = 0):
        pairs = str(pairs)
        duration_time = str(duration_time)
        udplength = str(udplength)

        if '.TRx' in direction:
            expected_tmp = int(expected) * 1.3
        else:
            expected_tmp = int(expected)

        highest_data = 0
        for retest in range(4):
            data, tx_data, rx_data =0, 0, 0
            log.Logger('**** Running ' + direction)
            socket_conn, socket_conn_else = False, False
            while True :
                socket_conn = self.socket.Connection(remoteIP, 9580)
                socket_conn_else = self.socket.Connection(remoteIP, 9580)

                if socket_conn and socket_conn_else:
                    self.killall_iperf(remoteIP, 'iperf3')
                    self.killall_iperf(remoteIP, 'iperf')
                    self.socket.Send(socket_conn, 'Clear buffer', 5)
                    break
                else:
                    log.Logger('**** Can not access ' + remoteIP)
                    time.sleep(2)
            
            if 'UDP' in direction:
                server_cmd = 'iperf -s -i 1 -u -f m'
                client_cmd = 'iperf -u -b ' + udpbandwidth + ' -f m -i 1 -t ' + duration_time
                client_cmd = client_cmd + ' -l ' + udplength
                if 'Tx' in direction:
                    port = 1111
                    que = queue.Queue()
                    cmd = server_cmd + ' -p ' + str(port) + ' divider ' + pairs
                    log.Logger('[To Remote PC] : ' + cmd, 'YELLOW')
                    iperf_server = threading.Thread(target=lambda q, arg1, arg2, arg3: que.put(self.socket.Send(arg1, arg2, arg3)), args=( que, socket_conn, cmd, int(duration_time) + 60 ) )
                    #iperf_server.setDaemon(True)
                    iperf_server.daemon = True
                    iperf_server.start()
                    time.sleep(int(pairs)*0.4)

                    names = locals()
                    for i in range(int(pairs)):
                        names[ 'iperf_client%s' % str(i)] = threading.Thread(target = self.iperf_shell, args=(client_cmd + ' -c ' + remoteIP + ' -p ' + str(port+i), ))
                        names[ 'iperf_client%s' % str(i)].daemon = True
                        names[ 'iperf_client%s' % str(i)].start()
                        time.sleep(0.2)
                    for i in range(int(pairs)):
                        names[ 'iperf_client%s' % str(i)].join()
                    time.sleep(1)
                    self.killall_iperf(remoteIP, 'iperf')
                    iperf_server.join()
                    All_pairs_throughput = que.get()
                    if All_pairs_throughput :
                        for i in All_pairs_throughput.split(','):
                            data = data + self.gerp_Iperf_Result(i)
                    tx_data, rx_data = 10, 10

                elif 'Rx' in direction and 'TR' not in direction:
                    port = 1111
                    names = locals()
                    for i in range(int(pairs)):
                        names[ 'que%s' % str(i)] = queue.Queue()
                        names[ 'iperf_server%s' % str(i)] = threading.Thread(target=lambda q, arg1: names['que%s' % str(i)].put(self.iperf_shell(arg1)), args=( names['que%s' % str(i)], server_cmd + ' -p ' + str(port+i) ))
                        names[ 'iperf_server%s' % str(i)].daemon = True
                        names[ 'iperf_server%s' % str(i)].start()
                        time.sleep(0.2)
                    cmd = client_cmd + ' -c ' + localIP + ' -p ' + str(port) +  ' divider ' + pairs 
                    log.Logger('[To Remote PC] : ' + cmd, 'YELLOW')
                    self.socket.Send(socket_conn, cmd, int(duration_time) + 60)
                    self.killall_iperf(remoteIP, 'iperf')
                    for i in range(int(pairs)):
                        names[ 'iperf_server%s' % str(i)].join()
                    for i in range(int(pairs)):
                        handle = names[ 'que%s' % str(i)].get()
                        data = data + handle
                    tx_data, rx_data = 10, 10

                elif 'TRx' in direction:
                    pairs_tmp = str(math.ceil(int(pairs)/2))
                    ### Tx_ser
                    tx_port = 1111
                    tx_que = queue.Queue()
                    cmd = server_cmd + ' -p ' + str(tx_port) + ' divider ' + pairs_tmp
                    log.Logger('[To Remote PC] : ' + cmd, 'YELLOW')
                    tx_server = threading.Thread(target=lambda q, arg1, arg2, arg3: tx_que.put(self.socket.Send(arg1, arg2, arg3)), args=( tx_que, socket_conn, cmd, int(duration_time) + 40 ) )
                    tx_server.daemon = True
                    tx_server.start()
                    time.sleep(1)
                    #### Rx_ser
                    rx_port = 2222
                    names = locals()
                    for i in range(int(pairs_tmp)):
                        names[ 'rx_que%s' % str(i)] = queue.Queue()
                        names[ 'rx_server%s' % str(i)] = threading.Thread(target=lambda q, arg1: names['rx_que%s' % str(i)].put(self.iperf_shell(arg1)), args=( names['rx_que%s' % str(i)], server_cmd + ' -p ' + str(rx_port+i) ))
                        names[ 'rx_server%s' % str(i)].daemon = True
                        names[ 'rx_server%s' % str(i)].start()
                        time.sleep(0.3)
                    ### Tx_client 
                    for i in range(int(pairs_tmp)):
                        names[ 'Tx_client%s' % str(i)] = threading.Thread(target = self.iperf_shell, args=(client_cmd + ' -c ' + remoteIP + ' -p ' + str(tx_port+i), ))
                        names[ 'Tx_client%s' % str(i)].daemon = True
                        names[ 'Tx_client%s' % str(i)].start()
                        time.sleep(0.2)
                    ### Rx_client
                    cmd = client_cmd + ' -c ' + localIP + ' -p ' + str(rx_port) +  ' divider ' + pairs_tmp
                    log.Logger('[To Remote PC] : ' + cmd, 'YELLOW')
                    rx_client = threading.Thread(target = self.socket.Send, args=(socket_conn_else, cmd, int(duration_time) + 40, ) )
                    rx_client.daemon = True
                    rx_client.start()
                    ### TxRx
                    for i in range(int(pairs_tmp)):
                        names[ 'Tx_client%s' % str(i)].join()
                    time.sleep(1)
                    self.killall_iperf(remoteIP, 'iperf')
                    for i in range(int(pairs_tmp)):
                        handle = names[ 'rx_que%s' % str(i)].get()
                        rx_data = rx_data + handle

                    All_pairs_throughput = tx_que.get()
                    if All_pairs_throughput:
                        for i in All_pairs_throughput.split(','):
                            tx_data = tx_data + self.gerp_Iperf_Result(i)
                    log.Logger('**** Tx Result : ' + str(tx_data))
                    log.Logger('**** Rx Result : ' + str(rx_data))
                    data = tx_data + rx_data

            elif 'TCP' in direction:
                iperf_ver = 'iperf3'
                server_cmd = iperf_ver + ' -s -i 1 -f m --forceflush'
                client_cmd = iperf_ver + ' -i 1 -t ' + duration_time + ' -f m --forceflush'
                if 'Tx' in direction:
                    que = queue.Queue()
                    log.Logger('[To Remote PC] : ' + server_cmd, 'YELLOW')
                    iperf_server = threading.Thread(target=lambda q, arg1, arg2, arg3: que.put(self.socket.Send(arg1, arg2, arg3)), args=( que, socket_conn, server_cmd, int(duration_time) + 60 ) )
                    iperf_server.daemon = True
                    iperf_server.start()
                    time.sleep(0.5)
                    data = self.iperf_shell(client_cmd + ' -c ' + remoteIP + ' -P ' + pairs)
                    tx_data, rx_data = 10, 10
                    self.killall_iperf(remoteIP, 'iperf3')
                    iperf_server.join()

                elif 'Rx' in direction and 'TR' not in direction:
                    que = queue.Queue()
                    iperf_server = threading.Thread(target=lambda q, arg1:que.put( self.iperf_shell(arg1)), args=(que, server_cmd ))
                    iperf_server.daemon = True
                    iperf_server.start()
                    time.sleep(1)
                    cmd = client_cmd + ' -c ' + localIP + ' -P ' + pairs
                    log.Logger('[To Remote PC] : ' + cmd, 'YELLOW')
                    self.socket.Send(socket_conn, cmd, int(duration_time) + 60)
                    self.killall_iperf(remoteIP, 'iperf3')
                    iperf_server.join()
                    data = que.get()
                    tx_data, rx_data = 10, 10

                elif 'TRx' in direction:
                    pairs_tmp = str(math.ceil(int(pairs)/2))
                    txque, rxque = queue.Queue(), queue.Queue()
                    cmd = server_cmd + ' -p 1111'
                    log.Logger('[To Remote PC] : ' + cmd, 'YELLOW')
                    tx_server = threading.Thread(target=lambda q, arg1, arg2, arg3: txque.put(self.socket.Send(arg1, arg2, arg3)), args=( txque, socket_conn, cmd, int(duration_time) + 60 ) )
                    tx_server.daemon = True
                    tx_server.start()
                    time.sleep(1)
                    rx_server = threading.Thread(target=lambda q, arg1: rxque.put(self.iperf_shell(arg1)), args=( rxque, server_cmd +  ' -p 2222' ) )
                    rx_server.daemon = True
                    rx_server.start()
                    time.sleep(1)

                    tx_client = threading.Thread(target = self.iperf_shell, args=(client_cmd + ' -c ' + remoteIP + ' -P ' + pairs_tmp + ' -p 1111', ))
                    tx_client.daemon = True
                    cmd = client_cmd + ' -c ' + localIP + ' -P ' + pairs_tmp + ' -p 2222'
                    log.Logger('[To Remote PC] : ' + cmd, 'YELLOW')
                    rx_client = threading.Thread(target = self.socket_Send, args=(socket_conn_else, cmd, int(duration_time) + 60,) )
                    rx_client.daemon = True

                    tx_client.start()
                    time.sleep(0.5)
                    rx_client.start()

                    tx_client.join()
                    rx_client.join()
                    self.killall_iperf(remoteIP, 'iperf3')
                    tx_data = txque.get()
                    rx_data = rxque.get()
                    if tx_data and rx_data:
                        tx_data = self.gerp_Iperf_Result(tx_data)
                        data = tx_data + rx_data
                    log.Logger('**** Tx Result : ' + str(tx_data))
                    log.Logger('**** Rx Result : ' + str(rx_data))

            data = round(data,2)
            log.Logger('**** ' + direction + ' Result : ' + str(data))
            if data == 0 or tx_data == 0 or rx_data == 0:
                log.Logger('**** Failed, ond side is "0".')
                return False
            elif data >= expected_tmp :
                break
            else:
                if data > highest_data:
                    highest_data = data
                if retest == 3 :
                    data = '*' + str(highest_data)
                    log.Logger('Return the highest result : ' + str(data))
                    break
                else:
                    log.Logger(str(highest_data) + ' < ' + str(expected_tmp) + ' Mbps, Retest ' + str(retest+1) + '...\n\n')

            self.socket.Disconnection()
            time.sleep(1)
        return data


    def iperf3_function(self, remoteIP, direction, wnicIP, pairs, duration_time, port='1111', spec=0.7, rate_from='wnic'):
        log.Logger( '**** Running ' + direction, 'BLACK', 'WHITE')
        pairs = str(pairs)
        duration_time = str(duration_time)
        highest_data = 0
        for retest in range(4):
            data, socket_conn, socket_conn_else = 0, False, False
            while True :
                socket_conn = self.socket.Connection(remoteIP, 9580)
                socket_conn_else = self.socket.Connection(remoteIP, 9580)

                if socket_conn and socket_conn_else:
                    self.killall_iperf(remoteIP, 'iperf3')
                    self.socket.Send(socket_conn, 'Clear buffer', 5)
                    break
                else:
                    log.Logger('**** Can not access ' + remoteIP)
                    time.sleep(2)
            que = queue.Queue()
            cmd = 'iperf3 -s -i 1 -f m -p ' + port + ' --forceflush'
            sub_process = threading.Thread(target=lambda q, arg1, arg2, arg3: que.put(self.socket.Send(arg1, arg2, arg3)), args=( que, socket_conn, cmd, int(duration_time) + 60 ) )
            sub_process.daemon = True
            sub_process.start()
            time.sleep(0.5)

            rate_que = queue.Queue()
            if rate_from == 'wnic':
                rate_task = threading.Thread(target=lambda q, arg1, arg2 : rate_que.put(self.socket.Rate_RSSI_Socket(arg1, arg2)), args=(rate_que, int(duration_time)/3, socket_conn_else ))
            elif rate_from == 'qca':
                rate_task = threading.Thread(target=lambda q, arg1, arg2 : rate_que.put(self.socket.Rate_RSSI_QCA(arg1, arg2)), args=(rate_que, int(duration_time)/3 ))
            rate_task.daemon = True
            rate_task.start()

            if 'Tx' in direction:
                cmd = 'iperf3 -c ' + wnicIP + ' -i 1 -f m -t ' + duration_time + ' -P ' + pairs + ' -p ' + port + ' --forceflush'
            elif 'Rx' in direction and 'TR' not in direction :
                cmd = 'iperf3 -c ' + wnicIP + ' -i 1 -f m -t ' + duration_time + ' -P ' + pairs + ' -p ' + port + ' -R --forceflush'
            elif 'TRx' in direction:
                cmd = 'iperf3 -c ' + wnicIP + ' -i 1 -f m -t ' + duration_time + ' -P ' + str(math.ceil(int(pairs)/2)) + ' --bidir -p ' + port + ' --forceflush'

            data = self.iperf3_shell(cmd)
            self.killall_iperf(remoteIP, 'iperf3')
            time.sleep(0.5)
            try:
                rate = rate_que.get(timeout=10)
                if rate_from == 'wnic' :
                    if 'Tx' in direction or 'TRx' in direction:
                        rate = float(rate['RXRATE'])
                    elif 'Rx' in direction:
                        rate = float(rate['TXRATE'])

                elif rate_from == 'qca' :
                    if 'Tx' in direction or 'TRx' in direction:
                        rate = float(rate['TXRATE'])
                    elif 'Rx' in direction:
                        rate = float(rate['RXRATE'])
                expected = rate * float(spec)
            except Exception as e:
                log.Logger('*** Error : ' + str(e), fore='', back='')
                rate = '*error'
                expected = 3000
            data = round(data,2)
            log.Logger('**** Link Rate : ' + str(rate), 'BLACK', 'YELLOW')
            log.Logger('**** ' + direction + ' Result : ' + str(data))

            if '.TRx' in direction:
                expected_tmp = expected * 1.3
            else:
                expected_tmp = expected
            #expected_tmp=0
            if data >= expected_tmp :
                break
            else:
                if data > highest_data:
                    highest_data = data
                if retest == 3 :
                    data = '*' + str(highest_data)
                    log.Logger('Return the highest result : ' + str(data))
                    break
                else:
                    log.Logger(str(highest_data) + ' < ' + str(expected_tmp) + ' Mbps, Retest ' + str(retest+1) + '...\n\n')

            self.socket.Disconnection()
            time.sleep(1)
        return data, rate



    def iperf_shell(self, strings):
        log.Logger(strings)
        string_split = strings.split(' ')
        command = os.popen(strings)
        tx_result, rx_result, result = '0 Mbits/sec', '0 Mbits/sec', '0 Mbits/sec'

        while True :
            tmp = command.buffer.readline().decode(encodeType, 'ignore')
            if (tmp == '') or ('WARNING' in tmp) or (('connected with' in tmp) and (result != '0 Mbits/sec')):
                break
            elif '-p' in string_split:
                tmp = 'port ' + string_split[string_split.index('-p')+1] + ' : ' + tmp
            tmp = tmp.replace('\n','')
            log.Logger(tmp)

            ### iperf3
            if ('--bidir' in strings) and ('receiver' in tmp):
                if '[TX-C]' in tmp:
                    tx_result = tmp
                elif '[RX-C]' in tmp:
                    rx_result = tmp
            elif 'receiver' in tmp :
                result = tmp

            ### iperf2, 只能用於udp及1pairs, 單向
            elif (' 0.00-' in tmp) and ('0.00-1.00' not in tmp) and ('out-of-order' not in tmp):
                result = tmp
                
        if ('--bidir' in strings):
            result = self.gerp_Iperf_Result(tx_result) + self.gerp_Iperf_Result(rx_result)
        else:
            result = self.gerp_Iperf_Result(result)
        
        return result


    def iperf3_shell(self, strings):
        log.Logger(strings, 'BLACK', 'WHITE')
        string_split = strings.split(' ')
        command = os.popen( strings)
        noreponse = 0
        tx_result, rx_result, result = '0 Mpbs/sec', '0 Mpbs/sec', '0 Mpbs/sec'
        while True :
            tmp = command.buffer.readline().decode(encodeType, 'ignore')
            if tmp == '':
                noreponse = noreponse + 1
                #log.Logger('PC : No reponse > ' + str(noreponse))
                time.sleep(1)
                if noreponse >= 7:
                    cmd = 'iperf3 error, stop.'
                    if '-p' in string_split:
                        cmd = 'port ' + string_split[string_split.index('-p')+1] + ' : ' + cmd
                    log.Logger(cmd, 'RED' )
                    break
                elif 3 < noreponse < 7:
                    cmd = 'iperf3 error, try again.'
                    if '-p' in string_split:
                        cmd = 'port ' + string_split[string_split.index('-p')+1] + ' : ' + cmd
                    log.Logger(cmd, 'RED')
                    command.flush()
                    time.sleep(0.1)
                    command = os.popen(strings)
            
            else:
                if '-p' in string_split:
                    tmp = 'port ' + string_split[string_split.index('-p')+1] + ' : ' + tmp.replace('\r', '').replace('\n', '')
                log.Logger(tmp)
                noreponse = 0
                if 'iperf Done' in tmp:
                    break

            if ('--bidir' in strings) and ('receiver' in tmp):
                if '[TX-C]' in tmp:
                    tx_result = tmp
                elif '[RX-C]' in tmp:
                    rx_result = tmp
            elif 'receiver' in tmp :
                result = tmp

        if ('--bidir' in strings):
            result = self.gerp_Iperf_Result(tx_result) + self.gerp_Iperf_Result(rx_result)
        else:
            result = self.gerp_Iperf_Result(result)
        return round(result,2)


    
    def gerp_Iperf_Result(self, handle):
        iperf_Result = 0
        handle = handle.split(' ')
        for i in range(len(handle)):
            if '/sec' in handle[i]:
                iperf_Result = float(handle[i-1])
        return round(iperf_Result,2)


    def killall_iperf(self, remoteIP, iperfver):
        cmd = 'kill ' + iperfver
        log.Logger('*** ' + cmd)
        killProcess(iperfver)
        conn = self.socket.Connection(remoteIP, 9580)
        if conn:
            try:
                log.Logger("[To Remote PC] : " + cmd)
                conn.settimeout(2)
                conn.sendall(cmd.encode())
                recvdata = conn.recv(1024)
                log.Logger(recvdata.decode() )
                time.sleep(1)
                self.socket.Disconnection(conn)
                return True
            except Exception as e:
                log.Logger(str(e))
                return False
        else:
            return False
