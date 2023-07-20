import telnetlib
import locale
encodeType = locale.getdefaultlocale()[1]


class Telnet:
    def __init__(self):
        None

    def Connect(self, ip):
        try:
            self.tn = telnetlib.Telnet(ip, timeout=1)
            return True
        except:
            log.Logger('Can not telnet ' + ip + ', Failed.')
            return False

    def Disconnect(self):
        try:
            self.tn.close()
        except:
            None

    def Write(self, cmd, excepted=''):
        bResult = False
        self.tn.write(cmd.encode('ascii') + b"\n")
        while True:
            line = self.tn.read_until(b"\n", timeout=0.3)  # Read one line
            line = str(line, encodeType).replace('\r\n', '')
            if line != '':
                log.Logger('Telnet : ' + line)
            if ":/#" in line and cmd not in line:  # last line, no more read
                return bResult
            elif excepted in line:
                bResult = True


