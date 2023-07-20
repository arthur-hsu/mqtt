import os, time
from config.lab_config import lab


def init():
    global _global_dict
    _global_dict = {}

    logFolder =  time.strftime( "%Y.%m.%d_%X", time.localtime() ).replace(":", "")
    root_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    root_dir = root_dir if 'GoogleDrive'.upper() not in root_dir.upper() else '/Users/reesehung/_Log'
    report_dir = '%s/_log/%s/' %(root_dir, logFolder)
    _global_dict['root_dir'] = root_dir+'/'

    _global_dict['report_path'] = report_dir
    _global_dict['buildOrder'] = logFolder

    _global_dict['screenshot_path'] = "{}screenshot/".format(report_dir)
    #_global_dict['download_path'] = "{}download/".format(report_dir)
    #_global_dict['upload_path'] = "{}upload/".format(report_dir)
    _global_dict['logname'] = 'collect_test'

    current_os = os.popen('uname -a')
    info = ''
    for i in current_os.readlines():
        info += '%s' %i 
    _global_dict['current_os'] = info 
    # pandas DF
    _global_dict['report_table'] = None

    _global_dict['driver'] = None

    _global_dict['serial'] = None

    _global_dict['lab'] = lab

    _global_dict['err'] = ['AT_BUSY_ERROR', 'NB_RECOVER', 'RDY', 'NB_ACTIVATE', 'Connected.', 'Disconnected.', 'NB_POWER_ON', 'NB_POWER_OFF', 'NORMAL POWER DOWN', 'NORMAL POWER ON']

    for i in _global_dict.keys():
        if 'path' in i and not os.path.exists(_global_dict[i]):
            os.makedirs(_global_dict[i])

def set_value(name, value):
    _global_dict[name] = value
    

def get_value(name, def_val=None):
    try: 
        return _global_dict[name]
    except :
        return def_val
