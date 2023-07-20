import serial.tools.list_ports
import pandas as pd
import os, platform, subprocess, queue, math
import threading
import locale
operation_system = platform.system()






class Chariot_Module:
    def Run(self, runtst_path, script_path, save_path, time, timeout):
        try:
            p = subprocess.run([runtst_path, script_path, save_path, '-t', str(time)], capture_output=True, shell=False, timeout=timeout, check=False)
            #p.stderr
            if 'Ending time' in str(p.stdout):
                return True
        except Exception as e:
            log.Logger('*** chariot run, failed')
            if 'timed' in e:
                log.Logger('time out...')
            else:
                log.Logger(str(e))
            return False
    
    def Data(self, fmttst_path, target_path, timeout=5):
        tmp_path = cf.get_value('report_path') + '/tmp.csv'
        try:
            p = subprocess.run([fmttst_path, "-v", target_path, tmp_path, '-s', '-q'], capture_output=True, shell=False, timeout=timeout, check=False)
            GROUP_AVERAGES = None
            data = []
            with open(tmp_path, 'r', encoding='utf-8-sig', errors='ignore') as f_input:
                for line in f_input:
                    data.append(list(line.strip().split(',')))
                dataset = pd.DataFrame(data)
                for i in range(dataset.shape[0]):
                    for x in range(dataset.shape[1]):
                        if dataset.loc[i][x] == 'GROUP AVERAGES':
                            GROUP_AVERAGES = True
                        if GROUP_AVERAGES and (dataset.loc[i][x] != None) and ('Throughput Avg.(' in dataset.loc[i][x]) :
                            unit = dataset.loc[i][x].replace("Throughput Avg.", '')
                            data = float(dataset.loc[i+1][x])
                f_input.close()
                os.remove(tmp_path)
            time.sleep(1)
        except Exception as e:
            log.Logger('*** chariot data, failed')
            log.Logger(str(e))
            unit, data = '(Mbps)', 0
        return unit, round(data, 2)


