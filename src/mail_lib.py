import smtplib, time, sys, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
# st=['aaa890177@gmail.com','arthur890177@gmail.com']
# p='/home/arthur/Desktop/mqtt/TEST_RESULT/2023.03.27_171547-test_mqtt.xlsx'
# f='2023.03.27_171547-test_mqtt.xlsx'


def send_mail(sendto='', path='', opentime='', dev=''):
    # 发件人和收件人的电子邮件地址
    sender_email = 'arthur.hsu@rakwireless.com'

    if sendto   == '' : sendto   = ['arthur890177@gmail.com','arthur.hsu.rak@gmail.com', 'kerry.hsu@rakwireless.com']
    if path     == '' : path     = False
    if opentime == '' : opentime = time.ctime()
    if dev      == '' : dev      = 'test_dev'
    # print('Send mail to:')
    # if type(sendto)==str: print(sendto)
    # else:
        # for mailaddr in sendto: print('\t%s'%mailaddr)
    # 创建一个带有附件的邮件对象
    message = MIMEMultipart()
    message['Subject'] = '%s Daily report' %opentime
    message['From'] = sender_email
    message['To'] = ', '.join(sendto)

    # 添加邮件正文
    text = 'Hi, all:\n\t%s %s Daily report is ready!\n\n\nBR. Arthur'%(opentime, dev)
    message.attach(MIMEText(text))

    print(message)
    #添加附件
    if path != False:
        filepath=(re.split(r'/',path)).pop()
        filename=(re.split(r'-',filepath)).pop()
        subtype=re.findall(r'\.\w*',filename)[0]
        print('Attachment :%s'%path)
        with open(path, 'rb') as f:
            attachment = MIMEApplication(f.read(), _subtype=subtype)
            attachment.add_header('Content-Disposition', 'attachment', filename=filepath)
            message.attach(attachment)

    # 使用 SMTP 服务器发送邮件
    smtp_server = 'mail.rakwireless.com'
    smtp_port = 587
    smtp_username = 'arthur.hsu@intl.rakwireless.com'
    smtp_password = 'aaa123844879'
    while True:
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.sendmail(sender_email, sendto, message.as_string())
            print('Mail send success!')
            break
        except KeyboardInterrupt:
            sys.exit()

        except Exception as e:
            print(e,e.__traceback__.tb_lineno)
            print('Mail send fail!')
            continue
sendto=''

# python3 mail_lib.py      

if __name__ == '__main__':
    sendto, path = '', ''
    if len(sys.argv) > 1:
        sendto = sys.argv[1]
        sendto = eval(sendto) 
        if len(sys.argv)>2:
            path = sys.argv[2]
    print(f'{sendto=}', f'{path=}')
    send_mail(sendto, path)

