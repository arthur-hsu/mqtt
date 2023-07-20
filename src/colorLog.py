from colorama import init, Fore, Back, Style
import os, time, platform
import config.config as cf
import threading

fore_dict = {'None': '', 'GREEN': Fore.GREEN, 'RED': Fore.RED, 'YELLOW': Fore.YELLOW, 'BLACK': Fore.BLACK,\
             'CYAN': Fore.CYAN, 'BLUE': Fore.BLUE, 'MAGENTA': Fore.MAGENTA}
back_dict = {'None': '', 'None': '', 'WHITE': Back.WHITE, 'YELLOW': Back.YELLOW}

#Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
#Back: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
if 'Windows' in platform.system():
    init(wrap=True)

def Logger( log, fore = 'None', back = 'None', timestamp = 1, logname=''):
    if timestamp == 1:
        log = '[%s]  %s' %(time.ctime(), log)
    if logname == '':
        logname = cf.get_value('logname')
    f = open(cf.get_value('report_path') + '%s.txt' %logname, 'a')
    print('\n%s' %log, file = f)
    f.close()
    if fore != 'None' or back != 'None':
        log = '%s%s%s%s' %(fore_dict[fore], back_dict[back], log, Style.RESET_ALL)
    print('\n%s' %log)


def colo_prt( log, fore = 'None', back = 'None', timestamp = 1, logname=''):
    if timestamp == 1:
        log = '[%s]  %s' %(time.ctime(), log)
    if fore != 'None' or back != 'None':
        log = '%s%s%s%s' %(fore_dict[fore], back_dict[back], log, Style.RESET_ALL)
    print('%s' %log)



def multi_thread(func):
    def run(*args, **kwargs):
        #Logger("\tMulti_thread for %s%s"%(func.__name__, args), fore='MAGENTA', timestamp=0)
        multi_ps= threading.Thread(target = func, args=args, kwargs=kwargs)
        multi_ps.daemon = True
        multi_ps.start()
    return run
