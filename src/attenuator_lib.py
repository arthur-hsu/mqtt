import requests




class Attenuator:
    def vaunix_attenuator(self, ip, freq, attn):
        freq = str(freq)
        attn = str(attn)
        try:
            for chnl in range(1, 5):
                r = requests.get(url = 'http://' + ip + '/setup.cgi?&chnl=' + str(chnl) + '&freq=' + freq + '&lattnsz=1.0&tattnsz=0.1&attn=' + attn, headers={'User-Agent': 'Mozilla/5.0'})
                time.sleep(0.1)
            r = requests.get(url = 'http://' + ip + '/data.shtm',headers={'User-Agent': 'Mozilla/5.0'})
            values = {}
            for i in r.text.split(';'):
                if i != '':
                    values[i.split('=')[0]] = i.split('=')[1]
            chnlfreq = values['chnlfreq'].split(',')
            chnlattn = values['chnlattn'].split(',')
            
            attenuator = {}
            for i in range(len(chnlfreq)):
                attenuator[ 'chnl ' + str(i+1)] = [chnlfreq[i], int(float(chnlattn[i]))]
            return attenuator
        except:
            print('Faild to access ' + ip)
            return None
