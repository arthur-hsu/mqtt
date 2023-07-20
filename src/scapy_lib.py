from scapy.all import *
from . import colorLog as log

class Scapy_Module:
    def Run(self, snifferCard, filterKey='', timeout=30, saveFile=1):
        packet_FileName = time.strftime( "%Y.%m.%d_%X", time.localtime() ).replace(":", "")
        self.filter = filterKey
        log.Logger('*** Sniffer $s $s sec' %(snifferCard, timeout), fore = 'BLACK', back = 'WHITE')
        dpkt = sniff(iface= snifferCard, prn=self.pktPrint, timeout = timeout)
        #dpkt = sniff(iface= snifferCard, prn=lambda x: x.summary(), timeout = timeout, stop_filter=stop_filter)
        log.Logger(str(dpkt), fore = 'GREEN')
        if saveFile ==1:
            wrpcap('%s%s_%s.pcap' %(initlogpath, packet_FileName, filterKey), dpkt)
        return dpkt

    def Parsing(self, packets, *args) :
        log.Logger('*** Parsing Packets ' + str(args), fore = 'BLACK', back = 'WHITE')
        args_lower = []
        for arg in args:
            args_lower.append(arg.lower())
        args = args_lower
        
        Result = []
        for packet in packets:
            packetContents = packet.show(dump=True)
            if all(arg in packetContents.lower() for arg in args) :
                packetTime = time.strftime( "%Y.%m.%d %X", time.localtime(packet.time))
                log.Logger('TimeStamp : ' + packetTime, fore = 'GREEN', timestamp=0)
                log.Logger('Summary   : ' + packet.summary(), fore = 'GREEN', timestamp=0)
                log.Logger(packetContents, timestamp=0)
                Result.append(packetTime)
                #hexdump(dpkt[0])
                #return 1
        log.Logger('\n[Result]\n' + str(Result), fore='GREEN', timestamp=0)
        return Result
        '''if packet.haslayer(Dot11) :
            if packet.type == 0 and packet.subtype == 8:
                if packet.addr2 not in ap_list:
                    ap_list.append(packet.addr2)
                    print("Access Point MAC: %s with SSID: %s " %(packet.addr2, packet.info))'''

    def pktPrint(self, pkt):
        '''if pkt.haslayer(Dot11Beacon):
            print('[+] Detected 802.11 Beacon Frame')
        elif pkt.haslayer(Dot11ProbeReq):
            print('[+] Detected 802.11 Beacon Probe Request Frame')
        elif pkt.haslayer(TCP):
            print('[+] Detected a TCP Packet')
        elif pkt.haslayer(DNS):
            print('[+] Detected a DNS Packet')'''
        if self.filter.lower() in pkt.summary().lower():
            log.Logger(pkt.summary())
    
    def help(self):
        print('Ex.1\n 1. Sniffer and filter "dhcp" from summary.\n 2. Parse the packets and verify the string "dhcp" from content.')
        print("     packets = sniffer.Run('en0', filterKey='dHcP', timeout=10)")
        print("     result = sniffer.Parsing(packets, 'dhcp', 'reQuEst')")

        print('Ex.2\n 1. Sniffer and filter "RIP" from summary.\n 2. Parse the packets and verify the string "rip, version   = 4" from content.')
        print("     packets = sniffer.Run('en4', filterKey='rip', timeout=70)")
        print("     result = sniffer.Parsing(packets, 'RIP header', 'version   = 4')")

