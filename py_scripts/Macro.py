import config.config as cf
import src.colorLog as log
from py_scripts import Config_Node
import sys, time, os, json, subprocess
import src.serial_lib as serial_lib





def at_busy(master):
    def check_join():
        master.write(cmd = 'ATC+DEBUG=0', expected='OK', makeTrue=1)
        master.write(cmd = 'ATC+TSMODE=0', expected='OK', makeTrue=1)
        master.write(cmd = 'AT+CFM=0', expected='OK', makeTrue=1)
        while True:
            master.set_timeout(2)
            if master.write('AT+NJS=?', 'AT+NJS=1'):
                master.set_timeout(5)
                break
            else:
                master.write('AT+JOIN=1:1:8:10','OK', makeTrue=1)
                master.set_timeout(120)
                master.write('','EVT:JOINED')
    check_join()

    log.Logger('Search ProbeID of GE', fore='BLACK', back='WHITE', timestamp=0)
    Max_Probe = 4
    for i in range(Max_Probe):
        dump = master.write('ATC+PRB_INFO=%s?'%(i+1), ['ATC+PRB_INFO'], makeTrue=1, dump_duration=3)
        if 'GE' in dump:
            Specific_Probe = i+1
            break
    log.Logger('\tSpecific_Probe = %s'%Specific_Probe, timestamp=0)
    for i in range(Max_Probe):
        Config_Node.Set_Configuration(master, prb_id=i+1, prb_intv=60, snsr_index='all',snsr_intv=60, snsr_rule=8, snsr_hthr=300, snsr_lthr=100, Max_Probe=Max_Probe)

    i = 0
    crash = 0
    while True:
        log.Logger('*** The %s round'%(i), 'BLUE', 'WHITE', timestamp=0)
        master.write(cmd = 'ATC+DEBUG=1', expected='OK', makeTrue=1)
        master.write(cmd = 'ATC+TSMODE=1', expected='OK', makeTrue=1)
        master.write(cmd = 'AT+DR=3', expected='OK', makeTrue=1)
        master.write(cmd = 'AT+CFM=1', expected='OK', makeTrue=1)
        while master.conn_status() == False:
            serial = serial_lib.Serial_Module('/dev/ttyACM0', 115200, 3, '',0.01)
            serial.write('ATC+PRB_CNT=?', '=4', 1)
            serial.write('ATC+BTADV=RAK9487', 'OK', 1)
            if master.connect('RAK9487'):
                serial.Close()
                check_join()
                crash += 1
                i = 0
                break
        Config_Node.Set_Configuration(master, prb_id=Specific_Probe, prb_intv=60, snsr_index='all',snsr_intv=60, snsr_rule=8, snsr_hthr=10, snsr_lthr=-100)
        time.sleep(2)
        Config_Node.Set_Configuration(master, prb_id=Specific_Probe, prb_intv=60, snsr_index='all',snsr_intv=60, snsr_rule=2, snsr_hthr=800, snsr_lthr=700)
        time.sleep(2)
        i += 2
        master.set_timeout(5)
        if i % 5 == 0 and master.write('AT+SEND=1:aabb', 'SEND_CONFIRMED_OK', makeTrue=10) == False:
            if master.conn_status():
                master.write('ATC+TSMODE=0', 'OK')
                log.Logger('\tLoRA is not reponse after  %s round\n\tChange to CLI Mode. (Crash %s)' %(i,crash), fore='RED', timestamp=0)
                return


