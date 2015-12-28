#--coding: utf-8 --

#from PySide import QtGui, QtCore

from parallel import *

from window import *

import platform, distutils.dir_util, distutils.errors, distutils.file_util #distutil over shututil http://stackoverflow.com/questions/15034151/copy-directory-contents-into-a-directory-with-python #import error on linux http://stackoverflow.com/questions/19097235/backing-up-copying-an-entire-folder-tree-in-batch-or-python

from QtSingleApplication import QtSingleApplication

import pygments, pygments.lexers, pygments.formatters


class Main(WebsocketWorkerMixinForMain, UIMixin):

    file_ignore_list = map(lambda each: each.upper(), ["desktop.ini","thumbs.db",".ds_store","icon\r",".dropbox",".dropbox.attr"])

    max_file_size = 1024*1024*50

    update_contacts_list_signal = QtCore.Signal(list)

    show_settings_dialog_signal = QtCore.Signal()

    outgoing_signal_for_worker = QtCore.Signal(dict)
    
    def __init__(self, app, singleton, *args, **kwargs):
        super(Main, self).__init__(*args, **kwargs)

        self.app = app
        self.singleton = singleton

        self.dpi = app.desktop().logicalDpiX()

        self.rsa_private_key = ""

        self.init_ui()
        self.singleton.messageReceived.connect(lambda msg: self.tray_icon.restore())

        #self.init_clipboard()
        #self.previous_hash = ""

        self.ws_worker = WebsocketWorker(self)
        self.init_ws_worker()

        self.contacts_list = []
        self.update_contacts_list_signal.connect(self.set_contacts_list)
        self.show_settings_dialog_signal.connect(lambda:SettingsDialog.show(self))


    def set_contacts_list(self, contacts_list):
        self.contacts_list = contacts_list

    def on_contacts_list_incoming(self, contacts_list):
        self.set_contacts_list(contacts_list)

    def init_ws_worker(self):
        self.ws_worker.incoming_clip_signal_for_main.connect(self.on_incoming_slot)
        #self.ws_worker.set_clip_signal_for_main.connect(self.on_set_new_clip_slot)
        self.ws_worker.status_signal_for_main.connect(self.on_set_status_slot)
        self.ws_worker.delete_clip_signal_for_main.connect(self.panel_tab_widget.on_incoming_delete)
        self.ws_worker.clear_list_signal_for_main.connect(self.panel_tab_widget.clearAllLists) #clear everything on disconnect, since a new connection will append the the list
        self.ws_worker.initialize_contacts_list_signal_for_main.connect(self.on_contacts_list_incoming)
        self.ws_worker.change_tab_icon_signal_for_main.connect(self.panel_tab_widget.onChangeTabIconSlot)
        self.ws_worker.set_rsa_key_signal_for_main.connect(self.on_set_rsa_keys)
        self.ws_worker.start()

    def on_set_rsa_keys(self, private_key_and_salt):
        des_rsa_private_key = private_key_and_salt["rsa_private_key"]
        rsa_pbkdf2_salt = private_key_and_salt["rsa_pbkdf2_salt"]
        password = settings.account.get("password")
        passphrase = PBKDF2(password, rsa_pbkdf2_salt, dkLen=24, count=1000, prf=lambda p, s: HMAC.new(p, s, SHA512).digest()).encode("hex")

        self.rsa_private_key = RSA.importKey(des_rsa_private_key, passphrase)


#   def init_clipboard(self):
#       self.clipboard = self.app.clipboard() #clipboard is in the QtGui.QApplication class as a static (class) attribute. Therefore it is available to all instances as well, ie. the app instance.#http://doc.qt.io/qt-5/qclipboard.html#changed http://codeprogress.com/python/libraries/pyqt/showPyQTExample.php?index=374&key=PyQTQClipBoardDetectTextCopy https://www.youtube.com/watch?v=nixHrjsezac
#       self.clipboard.dataChanged.connect(self.on_clip_change_slot) #datachanged is signal, doclip is slot, so we are connecting slot to handle signal


    def generic_timer(self, second, *chores):
        second*=1000
        self.timer  = QtCore.QTimer(self)
        self.timer.setInterval(second)  # Throw event timeout with an interval of 1000 milliseconds
        def do_chores():
            for each in chores:
                each()
        self.timer.timeout.connect(do_chores)  # this ensures clipboard stays alive
        self.timer.start()


    #def on_set_new_clip_slot

    @staticmethod
    def decodeClipDisplay(clip):
        return (clip or '').decode("base64").decode("zlib").decode("utf-8", "replace")
    
    @staticmethod
    def encodeClipDisplay(clip):
        return (clip or '').encode("utf-8", "replace").encode("zlib").encode("base64") #MUST ENCODE in base64 before transmitting obsfucated data #null clip causes serious looping problems, put some text! Prevent setText's TypeError: String or Unicode type required
        
    def closeEvent(self, event): #http://stackoverflow.com/questions/9249500/pyside-pyqt-detect-if-user-trying-to-close-window
        self.hide()
        event.ignore() #event.accept() exits #event.ignore() #stops from exiting
        #self.close() close the main wigdget, which then cuases app.exit()

    def closeReal(self):
        # if i don't terminate the worker thread, the app will crash (ex. windows will say python.exe stopped working)
        self.ws_worker.terminate() #http://stackoverflow.com/questions/1898636/how-can-i-terminate-a-qthread
        self.app.exit() #directly close the app

if __name__ == '__main__':
    app_id = '3B9D38D3-AAA6-476D-97CB-E547F623B96E'
    singleton = QtSingleApplication(app_id, sys.argv)
    if singleton.isRunning():
        singleton.sendMessage("restore")
        sys.exit(0)  # http://stackoverflow.com/questions/12712360/qtsingleapplication-for-pyside-or-pyqt

    app = QtGui.QApplication(sys.argv) #create mainloop
    ex = Main(app, singleton) #run widgets
    sys.exit(app.exec_())