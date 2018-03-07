# encoding=utf-8

import htmlPy
import os
import itchat
import time
from itchat.content import *
from threading import Thread
from pypinyin import lazy_pinyin
from PySide import QtCore


DEBUG = False
LOG_FILE = 'log.txt'


# Initial confiurations
app = htmlPy.AppGUI(title=u'微信群发机器人', maximized=False, plugins=True)

BASE_DIR = os.path.abspath(os.path.dirname('.'))
app.static_path = os.path.join(BASE_DIR, 'bootstrap\\')
app.template_path = os.path.join(BASE_DIR, 'templates\\')
app.web_app.setMinimumWidth(1050)
app.web_app.setMinimumHeight(723)
app.template = ('index.html', {})
log = open( LOG_FILE, 'wb+')

def write_log(string_args):
    try:
        content = time.strftime(u'%Y-%m-%d_%H:%M:%S', time.localtime(time.time()) ) + u'\t' + string_args
        gbk_content = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime(time.time()) ) + '\t' + str(string_args.encode('gbk'))
        app.evaluate_javascript("python_function_log('" + content + "')")
        print(gbk_content)
        log.write(gbk_content + '\r\n')
    except Exception as e:
        print e
    log.flush()

class SendMessageThread(QtCore.QThread):

    signal = QtCore.Signal(object)

    def __init__(self, val, msg, msg_type, msg_file, friend_delete, msg_interval, message_start):
        QtCore.QThread.__init__(self, parent=None)
        self.wechat = val
        self.message = msg
        self.message_type = msg_type
        self.message_file = msg_file
        self.friend_delete = friend_delete
        self.message_interval = msg_interval
        self.message_start = message_start - 1 if message_start > 1 else 0
        self.RUNNING = False

    def set_running(self, running):
        self.RUNNING = running

    def sync_msg(self, msg):
        self.signal.emit(msg)

    def run(self):
        # sort friends
        friends = sorted(self.wechat.get_friends(), key = lambda e:''.join(lazy_pinyin(e.get('NickName'))).replace(' ', '').lower())

        media_id = None
        #image
        if self.message_type == 1:
            upfile = self.wechat.upload_file(self.message_file, isPicture=True)
        #video
        elif self.message_type == 2:
            upfile = self.wechat.upload_file(self.message_file, isVideo=True)
        #file
        elif self.message_type == 3:
            upfile = self.wechat.upload_file(self.message_file)

        if self.message_type != 0:
            if upfile['BaseResponse']['Ret'] == 0:
                media_id = upfile['MediaId']
            else:
                self.sync_msg(upfile['BaseResponse']['ErrMsg'])
                self.sync_msg(u'文件无法上传！')
                return None

        for friend in range(self.message_start, len(friends) - 1):

            if not self.RUNNING:
                self.sync_msg(u'停止发送消息！')
                break

            try:

                if self.message_type == 1:
                    self.wechat.send_image(self.message_file, friends[friend]['UserName'], media_id)
                    self.sync_msg(u'发送图片给: ' + friends[friend]['NickName'])

                elif self.message_type == 2:
                    self.wechat.send_video(self.message_file, friends[friend]['UserName'], media_id)
                    self.sync_msg(u'发送视频给: ' + friends[friend]['NickName'])

                elif self.message_type == 3:
                    self.wechat.send_file(self.message_file, friends[friend]['UserName'], media_id)
                    self.sync_msg(u'发送文件给: ' + friends[friend]['NickName'])
                    
                else:
                    self.sync_msg(u'发送消息给: ' + friends[friend]['NickName'])

                if len(self.message) >= 1:
                    self.wechat.send_msg(self.message, friends[friend]['UserName'])

            except Exception as e:
                self.sync_msg(e)

            self.sync_msg(u'python_function_send("' + str(friend + 1) + '")')
            time.sleep(self.message_interval)

        self.sync_msg(u'消息发送完毕！')


# Handler Functions
class BindingClass(htmlPy.Object):

    def __init__(self):
        htmlPy.Object.__init__(self)
        self.messageThread = None
        self.RUNNING = False
        self.LOGINED = False


    @htmlPy.Slot(str, int, result=int)
    def binding_method(self, string_arg, int_arg):
        write_log(u'程序启动...')
        return 0

    @htmlPy.Slot(result=int)
    def form_function_login(self):
        if not self.LOGINED:
            itchat.auto_login(hotReload=True)
            self.LOGINED = True
            app.evaluate_javascript('python_function_login(0)')
            write_log(u'登陆成功！')
        else:
            itchat.logout()
            self.LOGINED = False
            self.RUNNING = False
            self.form_function_stop()
            app.evaluate_javascript('python_function_logout(0)')
            write_log(u'注销成功！')
        return 0

    @htmlPy.Slot(str)
    def sync_log(self, string_args):
        if 'python_function' in string_args:
            app.evaluate_javascript(string_args)
        else:
            write_log(string_args)

    @htmlPy.Slot(str, int, str, str, str, str, result=int)
    def form_function_start(self, content_msg, content_type, content_file, friend_delete, content_interval, message_start):

        if DEBUG:
            write_log(u"消息内容: " + content_msg)
            write_log(u"消息类型: " + str(content_type))
            write_log(u"媒体文件: " + content_file)
            write_log(u"媒体文件路径: " +  content_file.replace('file:///', '').replace('/', '\\'))
            write_log(u"是否删除: " + friend_delete)
            write_log(u"消息间隔: " + content_interval)
            app.evaluate_javascript('python_function_start(1)')

        if not self.RUNNING:
            write_log(u'开始群发')
            self.RUNNING = True
            file_fullpath = content_file.replace('file:///', '').replace('/', '\\')
            self.messageThread = SendMessageThread(
                                itchat, 
                                content_msg, 
                                content_type, 
                                file_fullpath, 
                                friend_delete, 
                                float(content_interval),
                                int(message_start))
            self.messageThread.daemon = True
            self.messageThread.set_running(self.RUNNING)
            self.messageThread.signal.connect(self.sync_log)
            self.messageThread.start()
            app.evaluate_javascript('python_function_start(1)')
        else:
            self.form_function_stop()
        return 0

    @htmlPy.Slot(result=int)
    def form_function_stop(self):
        write_log(u'停止群发')
        self.RUNNING = False
        if self.messageThread != None:
            self.messageThread.set_running(self.RUNNING)
        app.evaluate_javascript('python_function_start_over(1)')


app.bind(BindingClass())


# Instructions for running application
if __name__ == '__main__':
    app.start()
