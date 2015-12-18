#--coding: utf-8 --

import gevent
from gevent.event import AsyncResult

#from gevent.queue import Queue #CANNOT USE QUEUE BECAUSE GEVENT CANNOT SWITCH CONTEXTS BETWEEN THREADS

from functions import *
import views
from widgets import FancyListItemWidget, FancyListItem

import requests, datetime, socket
from requests_toolbelt import MultipartEncoderMonitor

#from ws4py.client.geventclient import WebSocketClient
from websocket import create_connection
from websocket import _exceptions
from PySide.QtGui import *
from PySide import QtCore

import encompress

class WebsocketWorkerMixinForMain(object):

    outgoingSignalForWorker = QtCore.Signal(dict)

    def on_incoming_slot(self, emitted):

        new_clip = emitted

        list_widget = self.panel_tab_widget.get_list_widget_from_clip_data(new_clip)

        #self.panel_tab_widget.setTabIcon(new_icon_tab,QIcon("images/new.png"))

        new_list_widget_item =  FancyListItem()
        new_list_widget_item.set_data(new_clip)

        list_widget.insertItem(0,new_list_widget_item) #add to top #http://www.qtcentre.org/threads/44672-How-to-add-a-item-to-the-top-in-QListWidget
        #list_widget.takeItem(5) #TODO replace 5 with user settings #removes last item

        new_widget = FancyListItemWidget(new_clip, new_list_widget_item)

        list_widget.setItemWidget(new_list_widget_item, new_widget ) #add the label

        list_widget.scroll_to_top()

class WebsocketWorker(QtCore.QThread):

    #This is the signal that will be emitted during the processing.
    #By including int as an argument, it lets the signal know to expect
    #an integer argument when emitting.
    incoming_clip_signal_for_main = QtCore.Signal(dict)
    set_clip_signal_for_main = QtCore.Signal(dict)
    status_signal_for_main = QtCore.Signal(tuple)
    delete_clip_signal_for_main = QtCore.Signal(list)
    StarClipSignalForMain = QtCore.Signal(dict)
    clear_list_signal_for_main = QtCore.Signal()
    closeWaitDialogSignalForMain = QtCore.Signal(dict)
    initialize_contacts_list_signal_for_main = QtCore.Signal(list)
    set_rsa_key_signal_for_main = QtCore.Signal(dict)
    change_tab_icon_signal_for_main = QtCore.Signal(set)
    
    session_id = uuid.uuid4()

    # You can do any extra things in this init you need, but for this example
    # nothing else needs to be done expect call the super's init
    def __init__(self, main):
        QtCore.QThread.__init__(self)
                
        self.main = main
        self.initialized = 0
        self.refilling_list = True
        self.OUTGOING_QUEUE = deque() # must use alternative Queue for non standard library thread and greenlets

        self.main.outgoingSignalForWorker.connect(self.on_outgoing_slot) #we have to use slots as gevent cannot talk to separate threads that weren't monkey_patched (QThreads are not monkey_patched since they are not pure python)
        
    #A QThread is run by calling it's start() function, which calls this run()
    #function in it's own "thread".
    
    def on_outgoing_slot(self, async_process):
        #PRINT("on_outgoing_slot", prepare)

        try:
            account = settings.account
        except AttributeError:
            self.status_signal_for_main.emit((views.not_connected_msg,"bad"))
            return
        
        data = async_process["data"]
        question = async_process["question"]
        
        if question == "Update?": #do cpu intesive data modification before sending
            if not data.get("container_name"): ##CHECK HERE IF CONTAINER EXISTS IN OTHER ITEMS
                file_names = data["file_names"]
                self.status_signal_for_main.emit(("Encrypting", "lock"))
                with encompress.Encompress(password = account.get("password"), directory = CONTAINER_DIR, file_names_encrypt = file_names) as container_name:
                    
                    data["container_name"] = container_name
                    LOG.info("on_outgoing_slot: Update?: container_name: %s" % container_name)

        if question == "Share?":

            download_container_if_not_exist(data, self.streaming_download_callback)  # no yielding (app.processEvents) needed since this is a separate thread

            container_name_old = data["container_name"] #guaranteed to have a container name
            password_old = data["decryption_key"]

            with encompress.Encompress(password = password_old, directory = CONTAINER_DIR, container_name_decrypt=container_name_old):
                password_new = Random.new().read(16)
                file_names = data["file_names"]
                with encompress.Encompress(password = password_new, directory = CONTAINER_DIR, file_names_encrypt = file_names) as container_name_new:
                    data['container_name'] = container_name_new
                    data["decryption_key"] = password_new #still raw need to encrypt with recipients public key in outgoing greenlet!
                    LOG.info("on_outgoing_slot: Share?: container_name: %s" % container_name_new)
                    LOG.info("on_outgoing_slot: Share?: decryption_key: %s" % data["decryption_key"])

        try:
            data['host_name'] = settings.device_name
        except AttributeError:
            data["host_name"] = host_name

        data["timestamp_client"] = time.time()    
        
        data["session_id"] = self.session_id
                
        send = dict(
            question = question,
            data=data
        )
        
        self.OUTGOING_QUEUE.append(send)

    def reconnect(self):
        try:
            account = settings.account
        except AttributeError:
            self.KEEP_RUNNING = 0
            self.main.show_settings_dialog_signal.emit()
        else:
            return create_connection(URL("ws",DEFAULT_DOMAIN, DEFAULT_PORT, "ws", email=account.get("email"), password=account.get("password"), ) ) #The geventclient's websocket MUST be runned here, as running it in __init__ would put websocket in main thread


    def run(self): #It arranges for the object’s run() method to be invoked in a separate thread of control.
        #GEVENT OBJECTS CANNOT BE RUNNED OUTSIDE OF THIS THREAD, OR ELSE CONTEXT SWITCHING (COROUTINE YIELDING) WILL FAIL! THIS IS BECAUSE QTHREAD IS NOT MONKEY_PATCHABLE

        self.RESPONDED_EVENT = AsyncResult() #keep events separate, as other incoming events may interfere and crash the app! Though TCP/IP guarantees in-order sending and receiving, non-determanistic events like "new clips" will definitely fuck up the order!
        #self.RESPONDED_LIVING_EVENT = AsyncResult()

        self.WSOCK = None
        
        self.KEEP_RUNNING = 1

        self.greenlets = [
            gevent.spawn(self.outgoing_greenlet),
            gevent.spawn(self.incoming_greenlet),
            # gevent.spawn(self.keepAliveGreenlet),
        ]
        
        self.green = gevent.joinall(self.greenlets)
        
    def worker_loop_decorator(workerGreenlet):
        def closure(self):
            while 1:
                gevent.sleep(1)
                if not self.KEEP_RUNNING:
                    continue #needed when username/password is incorrect, to pause the loop until a new password is set
                if self.WSOCK:
                    try:
                        workerGreenlet(self)
                    except (socket.error, _exceptions.WebSocketConnectionClosedException):
                        LOG.error("socket failure in: %s"%workerGreenlet.__name__)
                        self.status_signal_for_main.emit(("Reconnecting", "connect"))
                        self.WSOCK.close() #close the WSOCK

                        self.refilling_list = True
                    else:
                        continue
                try: #TODO INVOKE CLIP READING ON STARTUP! AFTER CONNECTION
                    self.WSOCK = self.reconnect()
                    self.clear_list_signal_for_main.emit() #clear list on reconnect or else a new list will be sent on top of previous
                except: #previous try will handle later
                    LOG.info("Couldn't connect!")
                    LOG.info("Closing modal dialogs")
                    self.closeWaitDialogSignalForMain.emit(dict(
                            success=False,
                            reason = views.disconnected_msg)
                    )
                    pass #block thread until there is a connection
        return closure

    @worker_loop_decorator
    def incoming_greenlet(self):

        LOG.info("Begin incoming greenlet")
    
        dump = self.WSOCK.recv()

        try:
            received = json.loads(str(dump)) #blocks
        except ValueError: #ValueError, occurs when socket closes unexpectedly
            raise socket.error
    
        answer = received["answer"]
        
        data   = received["data"]
        
        #Keep alive is handled by the websocket library itself (ie. it sends "alive?" pings that was done manually befor)
    
        #PUB SUB STYLE
        if answer == "@error":
            self.KEEP_RUNNING = 0
            self.status_signal_for_main.emit((data, "bad"))
            
        elif answer == "@connected":
            #if not hasattr(self,"initialized"):
            if not self.initialized:
                self.status_signal_for_main.emit(("Connected", "good"))
                self.initialized = 1
            else:
                self.status_signal_for_main.emit(("Reconnected", "good"))
            rsa_private_key = data["rsa_private_key"]
            rsa_pbkdf2_salt = data["rsa_pbkdf2_salt"]
            self.set_rsa_key_signal_for_main.emit(dict(rsa_private_key = rsa_private_key, rsa_pbkdf2_salt = rsa_pbkdf2_salt))
            self.initialize_contacts_list_signal_for_main.emit(data["initial_contacts"])

        elif answer == "@newest_clips":
            data.reverse() #so the clips can be displayed top down since each clip added gets pushed down in listwidget

            tabs_affected = set([])
            for each in data:
                #download_container_if_not_exist(each, self.streaming_download_callback) #TODO MOVE THIS TO AFTER ONDOUBLE CLICK TO SAVE BANDWIDTH #MUST download container first, as it may not exist locally if new clip is from another device
                self.incoming_clip_signal_for_main.emit(each) #TODO DO NOT STORE PREVIEW IN MOGNODB, INSTEAD DERIVE IT FROM THE CONTAINER HERE. THIS WAY WE DON'T HAVE TO ENCRYPT THE MONGODB DOCUMENT

                tabs_affected.add(each["system"])

            if not self.refilling_list: #THE FIRST ONE EVER WILL NOT SHOW
                self.change_tab_icon_signal_for_main.emit(tabs_affected)
            else:
                self.refilling_list = False

            latest = each
            
            not_this_device = latest["session_id"] != self.session_id
            is_clipboard = latest["system"] == "main"
            is_star = latest["system"] == "starred"
            is_notification = latest["system"] == "notification"
            is_share = latest["system"] == "share"

            # Done: Add user setting to disable this if he doesn't want to sync with the cloud!
            if is_clipboard and not_this_device: #do not allow setting from the same pc
                try:
                    if not settings.universal_clipboard:
                        return
                except AttributeError:
                    pass
                else:
                    self.set_clip_signal_for_main.emit(dict(new_clip = latest, block_clip_change_detection = True)) #this will set the newest clip only, thanks to self.main.new_clip!!!
            elif is_share:
                self.status_signal_for_main.emit(("You got an item from %s"%latest["host_name"], "good"))

        elif answer == "@get_contacts":
            contacts_list = data
            self.initialize_contacts_list_signal_for_main.emit(contacts_list)

        elif answer == "@delete_local":
            LOG.info(data["location"])
            self.delete_clip_signal_for_main.emit(data["location"])

        #REQUEST/RESPONSE STYLE (Handle data in outgoing_greenlet since it was the one that is expecting a response in order to yield control)
        elif "!" in answer: #IMPORTANT --- ALWAYS CHECK HERE WHEN ADDING A NEW ANSWER
            self.RESPONDED_EVENT.set(received) #true or false    
        
    def request_response(self, send): #todo change name
        #while 1: #mimic do while to prevent waiting before send #TODO PREVENT DUPLICATE SENDS USING UUID

        expect = uuid.uuid4()

        send["echo"] = expect #prevents responses coming after 5 seconds from being accepted

        self.WSOCK.send(json.dumps(send))

        received = self.RESPONDED_EVENT.wait(timeout=10) #AsyncResult.get will block until a result is set by another greenlet, after that get will not block anymore. NOTE- get will return exception! Use wait instead

        if received != None:

            inspect = received["echo"]

            if expect == inspect:
                self.RESPONDED_EVENT = AsyncResult() #setattr(self, event_name, AsyncResult()    )
        else:
            received = {}
            received["data"] = dict(
                success=False,
                reason = "Operation timed out!"
            )

        return received["data"]

    def streaming_download_callback(self, progress):
        percent = progress["percent_done"]
        if percent > 100.0:
            percent = 100.0
        self.status_signal_for_main.emit(("Downloading %.2f%%" % percent, "download"))

    def streaming_upload_callback(self, monitor, container_size): #FIXME App can CRASH if freq too high!
        bytes_read = float(monitor.bytes_read)
        done = (bytes_read/container_size*100.0)
        if done > 100.0:
            done = 100.0
        percent_done = "%.2f"%done
        #print "%s%%"%percent_done
        if once_every_second.check(): #WITHOUT THIS TOO MANY SIGNALS WILL BE SENT AND APP WILL CRASH
            self.status_signal_for_main.emit(("Uploading %s%%"%percent_done, "upload"))

    def ensure_container_upload(self, container_name):

        #first check if upload needed before updating
        data = self.request_response(dict(
            question = "Upload?",
            data = container_name
        ))
        if not data["success"]:
            return

        container_exists = data["container_exists"]

        if container_exists == False:
            container_path = os.path.join(CONTAINER_DIR, container_name)
            container_size = os.path.getsize(container_path)

            try:
                email = settings.account.get("email")
                password = settings.account.get("password")
                m = MultipartEncoderMonitor.from_fields(
                    fields={'email': email, 'password': password,
                            'upload': (container_name, open(container_path, 'rb'), "application/pastebeam")},
                    callback=lambda monitor : self.streaming_upload_callback(monitor, container_size)
                    )
                r = requests.post(URL("http", DEFAULT_DOMAIN, DEFAULT_PORT, "upload"), data = m, headers={'Content-Type': m.content_type}) #files={"upload": open(container_path, 'rb')}) #old way of using requests file upload which does not allow customization of request
            except requests.exceptions.ConnectionError:
                #connection error
                raise socket.error


    @worker_loop_decorator
    def outgoing_greenlet(self):
                    
        try:
            send = self.OUTGOING_QUEUE.pop()
        except IndexError:
            return
        else:
            data_out = send.get("data")
            question = send["question"]

        LOG.debug(data_out)

        if question == "Share?":

            self.status_signal_for_main.emit(("Sharing", "share"))

            email = data_out["recipient"]

            public_key_success = self.request_response(dict(
                question = "Publickey?",
                data = email
            ))
            recipient_public_key = public_key_success["success"]

            if not recipient_public_key:
                return #SHOW MESSAGE HERE

            container_name = data_out["container_name"]
            self.ensure_container_upload(container_name)

            rsa_public_key = RSA.importKey(recipient_public_key)
            data_out["decryption_key"] = Binary(rsa_public_key.encrypt(data_out["decryption_key"], K=None)[0]) #K is ignored, but needed for compatibility # You will see a "$type" in the json, explanation: Binary data in MongoDB stores a "type" field, which can be any integer between 0 and 255. Identical data will only match if the subtype is the same.

            data_in = self.request_response(dict(
                question = "Share?",
                data = data_out
            ))
            if data_in['success']:
                self.status_signal_for_main.emit(("Your item was sent", "good"))
            else:
                #print "sh"+data_in["reason"]
                self.status_signal_for_main.emit((data_in["reason"], "warn"))

        if question == "Update?":
                    
            container_name = data_out["container_name"]

            self.ensure_container_upload(container_name)

            self.status_signal_for_main.emit(("Updating item to server", "sync"))

            data_in = self.request_response(send)

            if data_in["success"]:
                 self.status_signal_for_main.emit(("Updated", "good"))
            else:
                #print "upd"+data_in["reason"]
                self.status_signal_for_main.emit((data_in["reason"], "warn"))

        elif question=="Delete?":

            self.status_signal_for_main.emit(("Deleting", "trash"))

            data_in = self.request_response(send)

            if data_in["success"] == True:
                LOG.debug("DELETE! %s" % data_in)
                self.status_signal_for_main.emit(("Deleted from server", "good"))
            else:
                #print "del"+data_in["reason"]
                self.status_signal_for_main.emit((data_in["reason"], "warn"))
                    
        elif question=="Star?":
        
            self.status_signal_for_main.emit(("Adding to bookmarks", "star"))
            data_in = self.request_response(send)
            
            if data_in["success"]:
                self.status_signal_for_main.emit(("Added to your bookmarks!", "good"))
            else:
                #print "star"+data_in["reason"]
                self.status_signal_for_main.emit((data_in["reason"], "warn"))

        elif question=="Contacts?": #change to set_contacts?
            
            data_in = self.request_response(send)
            
            self.closeWaitDialogSignalForMain.emit(data_in)

        elif question=="Invite?":
            
            data_in = self.request_response(send)

            self.closeWaitDialogSignalForMain.emit(data_in)
            
        elif question =="Accept?":
            
            data_in = self.request_response(send)
            
            self.closeWaitDialogSignalForMain.emit(data_in)
            
