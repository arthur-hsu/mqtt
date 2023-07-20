import time, os, re, sys
import pathlib



at_files_path = '/Users/reesehung/Google Drive/我的雲端硬碟/RAK_Automation/RAK3172/Boundary_script/tmp'
print(at_files_path)

handle = ["include 'ed.init.ttl'", 'sendln ', '"', "include 'gen.result.ttl'", 'wait ', "include 'gen.result.ttl'", "flushrecv", "include 'pre.msg.ttl'", "AT_ERROR", "AT_BUSY_ERROR", "OK", "   "]

for file in os.listdir(at_files_path):
    if 'ttl' in file and 'py' not in file:
        print(file)
        fp = open(at_files_path + '/' + file, "r", encoding='utf-8')
        final = open(at_files_path + '/' + file.replace('.ttl', '.txt'), 'a')
        i=0
        while True :
            tmp = fp.readline().replace('\ufeff', '').replace('\n','')
            if i > 50:
                break
            if tmp == '':
                i += 1
            else:
                for string in handle:
                    if 'wait' in string:
                        tmp = tmp.replace(string, '    ')
                    else:
                        tmp = tmp.replace(string, '')
                i = 0
            print(tmp, file = final)
        final.close()
        fp.close()


