import paramiko
from paramiko_expect import SSHClientInteraction
import os
import time
from . import colorLog as log


class SSH_Module:
    def __init__(self, remote_ip, username='root', password='root', remote_ssh_port=22):
        ## createSSHClient
        self.host = remote_ip
        log.Logger('*** ssh %s@%s' %(username, remote_ip ), 'BLACK', 'WHITE', timestamp=0)
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname = remote_ip, port = remote_ssh_port, username = username, password = password )
        ## scp = SCPClient(self.ssh.get_transport())
    

    def send_command(self, cmd, dump=0, prompt=r".*~#\s*", timeout=10):
        timeout = 10 if not timeout else timeout
        for i in range(3):
            try:
                # Create a client interaction class which will interact with the host
                with SSHClientInteraction(self.ssh, timeout=3, display=False) as interact:
                    interact.expect(prompt) ## flush
                    interact.send(cmd)
                    interact.expect(prompt)
                    response = interact.current_output_clean
                    for line in response.split('\n'):
                        if line != '':
                            log.Logger("%s: %s" %(self.host, line))    
                    if dump == 1:
                        return response
                    else:
                        return True

            except Exception as e:
                log.Logger(str(e), fore='RED', timestamp=0)    
                log.Logger('Send command again.', timestamp=0)
                return False
            


    def disconnect(self):
        log.Logger("\tFinished the SSH Session %s" % self.host, fore='GREEN', timestamp=0)
        #self.ssh_stdin.close()
        #self.ssh_stdout.close()
        #self.ssh_stderr.close()
        self.ssh.close()

    
    




class SFTP_Module:
    def __init__(self, remote_ip, remote_ssh_port=22, username='root', password='root'):
        self.t = paramiko.Transport((remote_ip, remote_ssh_port))
        self.t.connect(username = ssh_username, password = ssh_password)
        self.sftp = paramiko.SFTPClient.from_transport(t)



    def Download_Image_To_Local(image_forder):
        remote_path = '/home/qa/Reese/%s/image/' %image_forder
        local_dir = '/home/'
        try:
            remote_dir = self.sftp.listdir(remote_path)
            for i in remote_dir:
                log.Logger('Downloading %s...' %i)
                self.sftp.get(remote_path + i, local_dir + i)
        except Exception as e:
            log.Logger(str(e), fore='RED')
            log.Logger('Server connection dropped when downloading image, try again after 30 sec.')
            return False

