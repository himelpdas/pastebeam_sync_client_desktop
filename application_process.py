#--coding: utf-8 --

#from PySide import QtGui, QtCore

from application_websocket_thread import *

from application_window import *

from Crypto.Hash import HMAC, SHA512
from Crypto.Protocol.KDF import PBKDF2

import multiprocessing, sys

from QtSingleApplication import QtSingleApplication

"""
We will use PyQt4 since it has cool features not available for PySide like global hotkeys (plugin) and singleton.
"""

class Main(WebsocketWorkerMixinForMain, UIMixin):

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


    def generic_timer(self, second, *chores):
        second*=1000
        self.timer  = QtCore.QTimer(self)
        self.timer.setInterval(second)  # Throw event timeout with an interval of 1000 milliseconds
        def do_chores():
            for each in chores:
                each()
        self.timer.timeout.connect(do_chores)  # this ensures clipboard stays alive
        self.timer.start()


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


class ConsumerClipboardChangedQueueListenerThread(QtCore.QThread):

    clipboard_changed_signal = QtCore.pyqtSignal(dict)

    def __init__(self, kill_event, clip_change_queue, *args, **kwargs):
        LOG.info("Pastebeam: Consumer: ConsumerClipboardChangedQueueListenerThread " + multiprocessing.current_process().name)

        self.clip_change_queue = clip_change_queue
        self.kill_event = kill_event

        super(self.__class__, self).__init__(*args, **kwargs)

    def run(self):
        while 1:
            clip_prepare = self.clip_change_queue.get()
            if clip_prepare is False or self.kill_event.is_set():  # poison pill technique
                break
            self.clipboard_changed_signal.emit(clip_prepare)


class ConsumerStatusQueueListenerThread(QtCore.QThread):

    status_signal = QtCore.pyqtSignal(tuple)

    def __init__(self, kill_event, status_queue, *args, **kwargs):
        LOG.info("Pastebeam: Consumer: ConsumerStatusQueueListenerThread " + multiprocessing.current_process().name)

        self.status_queue = status_queue
        self.kill_event = kill_event

        super(self.__class__, self).__init__(*args, **kwargs)

    def run(self):
        while 1:
            print "NEW STATUS LISTEN"
            status = self.status_queue.get()
            if status is False or self.kill_event.is_set():  # poison pill technique
                LOG.info("Pastebeam: Consumer: ConsumerStatusQueueListenerThread " + "Breaking")
                break
            self.status_signal.emit(status)


class Consumer(Main):

    def __init__(self, app, clip_change_queue, set_clip_queue, status_queue, kill_event, previous_hash, *args, **kwargs):
        LOG.info("Pastebeam: Consumer: __init__: " + multiprocessing.current_process().name)

        self.next_producer = kwargs.pop("next_producer")  # get rid of next_producer or else super init will raise TypeError for unknown kwarg

        app_id = '3B9D38D3-AAA6-476D-97CB-E547F623B96E'
        singleton = QtSingleApplication(app_id, sys.argv)
        if singleton.isRunning():
            singleton.sendMessage("restore")
            #sys.exit(0)  # http://stackoverflow.com/questions/12712360/qtsingleapplication-for-pyside-or-pyqt
            return

        super(self.__class__, self).__init__(app, singleton=singleton, *args, **kwargs)

        self.clip_change_queue = clip_change_queue
        self.set_clip_queue = set_clip_queue
        self.status_queue = status_queue
        self.kill_event=  kill_event
        self.previous_hash = previous_hash

        #self.main_widget = QtGui.QTextEdit()
        #self.setCentralWidget(self.main_widget)

        self.clipboard_event_thread = ConsumerClipboardChangedQueueListenerThread(self.kill_event, self.clip_change_queue)
        self.clipboard_event_thread.clipboard_changed_signal.connect(self.on_clipboard_changed)
        self.clipboard_event_thread.start()

        self.status_event_thread = ConsumerStatusQueueListenerThread(self.kill_event, self.status_queue)
        self.status_event_thread.status_signal.connect(self.on_set_status_slot)
        self.status_event_thread.start()


    def on_clipboard_changed(self, clip_prepare):

        hash_hex = clip_prepare["data"]["hash"]

        try:
            container_name = self.panel_tab_widget.get_matching_containers_for_hash(hash_hex).next()
            clip_prepare["container_name"] = container_name  # only need first
        except StopIteration:
            pass

        self.outgoing_signal_for_worker.emit(clip_prepare)

    def closeReal(self, close_event):
        self.clip_change_queue.put_nowait(False)
        self.status_queue.put_nowait(False)
        self.next_producer.set()
        self.kill_event.set()
