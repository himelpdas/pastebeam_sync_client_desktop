#--coding: utf-8 --

import gevent
from gevent.event import AsyncResult

#from gevent.queue import Queue #CANNOT USE QUEUE BECAUSE GEVENT CANNOT SWITCH CONTEXTS BETWEEN THREADS

from functions import *
from widgets import FancyListWidgetItem

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

    def onIncomingSlot(self, emitted):

        new_clip = emitted

        list_widget = self.panel_tab_widget.getListWidgetFromClip(new_clip)

        #self.panel_tab_widget.setTabIcon(new_icon_tab,QIcon("images/new.png"))

        new_list_widget_item =  QListWidgetItem()
        new_list_widget_item.setData(QtCore.Qt.UserRole, json.dumps(new_clip)) #json.dumps or else clip data (especially BSON's Binary)will be truncated by setData
        list_widget.insertItem(0,new_list_widget_item) #add to top #http://www.qtcentre.org/threads/44672-How-to-add-a-item-to-the-top-in-QListWidget
        list_widget.takeItem(5) #TODO replace 5 with user settings #removes last item

        new_widget = FancyListWidgetItem(new_clip, new_list_widget_item)

        list_widget.setItemWidget(new_list_widget_item, new_widget ) #add the label

        #move the scrollbar to top
        list_widget_scrollbar = list_widget.verticalScrollBar() #http://stackoverflow.com/questions/8698174/how-to-control-the-scroll-bar-with-qlistwidget
        list_widget_scrollbar.setValue(0)

class WebsocketWorker(QtCore.QThread):

    #This is the signal that will be emitted during the processing.
    #By including int as an argument, it lets the signal know to expect
    #an integer argument when emitting.
    incomingClipsSignalForMain = QtCore.Signal(dict)
    setClipSignalForMain = QtCore.Signal(dict)
    statusSignalForMain = QtCore.Signal(tuple)
    deleteClipSignalForMain = QtCore.Signal(list)
    StarClipSignalForMain = QtCore.Signal(dict)
    clearListSignalForMain = QtCore.Signal()
    closeWaitDialogSignalForMain = QtCore.Signal(dict)
    InitializeContactsListSignalForMain = QtCore.Signal(list)
    SetRSAKeySignalForMain = QtCore.Signal(dict)
    changeTabIconSignalForMain = QtCore.Signal(set)
    
    session_id = uuid.uuid4()

    # You can do any extra things in this init you need, but for this example
    # nothing else needs to be done expect call the super's init
    def __init__(self, main):
        QtCore.QThread.__init__(self)
                
        self.main = main
        self.initialized = 0
        self.refilling_list = True
        self.current_login = getLogin()
        self.OUTGOING_QUEUE = deque() # must use alternative Queue for non standard library thread and greenlets

        self.main.outgoingSignalForWorker.connect(self.onOutgoingSlot) #we have to use slots as gevent cannot talk to separate threads that weren't monkey_patched (QThreads are not monkey_patched since they are not pure python)
        
    #A QThread is run by calling it's start() function, which calls this run()
    #function in it's own "thread".
    
    def onOutgoingSlot(self, async_process):
        #PRINT("onOutgoingSlot", prepare)
        
        data = async_process["data"]
        question = async_process["question"]
                
        if question == "Delete?":
            pass #nothing to process
            
        if question == "Star?":
            pass
        
        if question == "Update?": #do cpu intesive data modification before sending

            if not data.get("container_name"): ##CHECK HERE IF CONTAINER EXISTS IN OTHER ITEMS
                file_names = data["file_names"]
                self.statusSignalForMain.emit(("Encrypting", "lock"))
                with encompress.Encompress(password = getLogin().get("password"), directory = CONTAINER_DIR, file_names_encrypt = file_names) as container_name:
                    
                    data["container_name"] = container_name
                    PRINT("encompress", container_name)

        if question == "Share?":

            container_name_old = data["container_name"]
            password_old = data["decryption_key"]
            with encompress.Encompress(password = password_old, directory = CONTAINER_DIR, container_name=container_name_old):
                password_new = Random.new().read(16)
                file_names = data["file_names"]
                with encompress.Encompress(password = password_new, directory = CONTAINER_DIR, file_names_encrypt = file_names) as container_name_new:
                    data['container_name'] = container_name_new
                    data["decryption_key"] = password_new #still raw need to encrypt with recipients public key in outgoing greenlet!

        data['host_name'] = getDeviceNameFromKeyring()#self.main.HOST_NAME

        data["timestamp_client"] = time.time()    
        
        data["session_id"] = self.session_id
                
        send = dict(
            question = question,
            data=data
        )
        
        self.OUTGOING_QUEUE.append(send)
    
    def run(self): #It arranges for the object’s run() method to be invoked in a separate thread of control.
        #GEVENT OBJECTS CANNOT BE RUNNED OUTSIDE OF THIS THREAD, OR ELSE CONTEXT SWITCHING (COROUTINE YIELDING) WILL FAIL! THIS IS BECAUSE QTHREAD IS NOT MONKEY_PATCHABLE
    
        self.RESPONDED_EVENT = AsyncResult() #keep events separate, as other incoming events may interfere and crash the app! Though TCP/IP guarantees in-order sending and receiving, non-determanistic events like "new clips" will definitely fuck up the order!
        #self.RESPONDED_LIVING_EVENT = AsyncResult()
        
        self.RECONNECT = lambda: create_connection(URL("ws",DEFAULT_DOMAIN, DEFAULT_PORT, "ws", email=getLogin().get("email"), password=getLogin().get("password"), ) ) #The geventclient's websocket MUST be runned here, as running it in __init__ would put websocket in main thread
        
        self.WSOCK = None
        
        self.KEEP_RUNNING = 1

        self.greenlets = [
            gevent.spawn(self.outgoingGreenlet),
            gevent.spawn(self.incomingGreenlet),
            # gevent.spawn(self.keepAliveGreenlet),
        ]
        
        self.green = gevent.joinall(self.greenlets)
        
    def workerLoopDecorator(workerGreenlet):
        def closure(self):
            while 1:
                gevent.sleep(1)
                if not self.KEEP_RUNNING:
                    continue #needed when username/password is incorrect, to pause the loop until a new password is set
                if self.WSOCK:
                    try:
                        workerGreenlet(self)
                    except (socket.error, _exceptions.WebSocketConnectionClosedException):
                        PRINT("failure in", workerGreenlet.__name__)
                        self.statusSignalForMain.emit(("Reconnecting", "connect"))
                        self.WSOCK.close() #close the WSOCK

                        self.refilling_list = True
                    else:
                        continue
                try: #TODO INVOKE CLIP READING ON STARTUP! AFTER CONNECTION
                    self.WSOCK = self.RECONNECT()
                    self.clearListSignalForMain.emit() #clear list on reconnect or else a new list will be sent on top of previous
                except: #previous try will handle later
                    LOG.info("Couldn't connect!")
                    LOG.info("Closing modal dialogs")
                    self.closeWaitDialogSignalForMain.emit(dict(
                            success=False,
                            reason = "Got disconnected!")
                    )
                    pass #block thread until there is a connection
        return closure

    @workerLoopDecorator
    def incomingGreenlet(self):

        LOG.info("Begin incoming greenlet")
    
        dump = self.WSOCK.recv()

        try:
            received = json.loads(str(dump)) #blocks
        except ValueError: #occurs when socket closes unexpectedly
            raise socket.error
    
        answer = received["answer"]
        
        data   = received["data"]
        
        #Keep alive is handled by the websocket library itself (ie. it sends "alive?" pings that was done manually befor)
    
        #PUB SUB STYLE
        if answer == "Error!":
            self.KEEP_RUNNING = 0
            self.statusSignalForMain.emit((data, "bad"))
            
        elif answer == "Connected!":
            #if not hasattr(self,"initialized"):
            if not self.initialized:
                self.statusSignalForMain.emit(("Connected", "good"))
                self.initialized = 1
            else:
                self.statusSignalForMain.emit(("Reconnected", "good"))
            rsa_private_key = data["rsa_private_key"]
            rsa_pbkdf2_salt = data["rsa_pbkdf2_salt"]
            self.SetRSAKeySignalForMain.emit(dict(rsa_private_key = rsa_private_key, rsa_pbkdf2_salt = rsa_pbkdf2_salt))
            self.InitializeContactsListSignalForMain.emit(data["initial_contacts"])

        elif answer == "Newest!":
            data.reverse() #so the clips can be displayed top down since each clip added gets pushed down in listwidget

            tabs_affected = set([])
            for each in data:
            
                #downloadContainerIfNotExist(each, self.streamingDownloadCallback) #TODO MOVE THIS TO AFTER ONDOUBLE CLICK TO SAVE BANDWIDTH #MUST download container first, as it may not exist locally if new clip is from another device
                self.incomingClipsSignalForMain.emit(each) #TODO DO NOT STORE PREVIEW IN MOGNODB, INSTEAD DERIVE IT FROM THE CONTAINER HERE. THIS WAY WE DON'T HAVE TO ENCRYPT THE MONGODB DOCUMENT

                tabs_affected.add(each["system"])

            if not self.refilling_list: #THE FIRST ONE EVER WILL NOT SHOW
                self.changeTabIconSignalForMain.emit(tabs_affected)
            else:
                self.refilling_list = False

            latest = each
            
            not_this_device = latest["session_id"] != self.session_id
            is_clipboard = latest["system"] == "main"
            is_star = latest["system"] == "starred"
            is_notification = latest["system"] == "notification"
            is_share = latest["system"] == "share"

            #TODO- add user setting to disable this if he doesn't want to sync with the cloud!
            if is_clipboard and not_this_device: #do not allow setting from the same pc
                self.setClipSignalForMain.emit(dict(new_clip = latest, block_clip_change_detection = True)) #this will set the newest clip only, thanks to self.main.new_clip!!!
            elif is_share:
                self.statusSignalForMain.emit(("You got something from %s"%latest["host_name"], "good"))
            """
            if is_clipboard:
                self.statusSignalForMain.emit(("clipboard synced to cloud", "good"))
                if not_this_device: #do not allow setting from the same pc
                    self.setClipSignalForMain.emit(latest) #this will set the newest clip only, thanks to self.main.new_clip!!!
            elif is_star:
                self.statusSignalForMain.emit(("added item to bookmarks", "good"))
            elif is_share:
                self.statusSignalForMain.emit(("you got something from %s"%latest["host_name"], "good"))
            elif is_notification:
                self.statusSignalForMain.emit(("you have a new notification", "good"))
            """

        elif answer == "get_contacts!":
            contacts_list = data
            self.InitializeContactsListSignalForMain.emit(contacts_list)

        elif answer == "delete_local":
            self.deleteClipSignalForMain.emit(data["location"])

        #REQUEST/RESPONSE STYLE (Handle data in outgoing_greenlet since it was the one that is expecting a response in order to yield control)
        elif answer in ["Upload!", "Update!", "Delete!", "Star!", "Contacts!", "Invite!", "Accept!", "Publickey!", "Share!"]: #IMPORTANT --- ALWAYS CHECK HERE WHEN ADDING A NEW ANSWER
            self.RESPONDED_EVENT.set(received) #true or false    
        
    def requestResponse(self, send): #todo change name
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

    def streamingDownloadCallback(self, progress):
        self.statusSignalForMain.emit(("Downloading %s"%progress["percent_done"], "download"))

    def streamingUploadCallback(self, monitor, container_size): #FIXME App can CRASH if freq too high!
        bytes_read = float(monitor.bytes_read)
        percent_done = "%.2f"%(bytes_read/container_size*100.0)
        #print "%s%%"%percent_done
        if once_every_second.check(): #WITHOUT THIS TOO MANY SIGNALS WILL BE SENT AND APP WILL CRASH
            self.statusSignalForMain.emit(("Uploading %s%%"%percent_done, "upload"))

    def ensureContainerUpload(self, container_name):

        #first check if upload needed before updating
        data = self.requestResponse(dict(
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
                email = self.current_login.get("email")
                password = self.current_login.get("password")
                m = MultipartEncoderMonitor.from_fields(
                    fields={'email': email, 'password': password,
                            'upload': (container_name, open(container_path, 'rb'), "application/pastebeam")},
                    callback=lambda monitor : self.streamingUploadCallback(monitor, container_size)
                    )
                r = requests.post(URL("http", DEFAULT_DOMAIN, DEFAULT_PORT, "upload"), data = m, headers={'Content-Type': m.content_type}) #files={"upload": open(container_path, 'rb')}) #old way of using requests file upload which does not allow customization of request
            except requests.exceptions.ConnectionError:
                #connection error
                raise socket.error


    @workerLoopDecorator
    def outgoingGreenlet(self):
                    
        try:
            send = self.OUTGOING_QUEUE.pop()
        except IndexError:
            return
        else:
            data_out = send.get("data")
            question = send["question"]

        if question == "Share?":

            self.statusSignalForMain.emit(("Sharing", "share"))

            email = data_out["recipient"]

            public_key_success = self.requestResponse(dict(
                question = "Publickey?",
                data = email
            ))
            recipient_public_key = public_key_success["success"]

            if not recipient_public_key:
                return #SHOW MESSAGE HERE


            container_name = data_out["container_name"]
            self.ensureContainerUpload(container_name)

            rsa_public_key = RSA.importKey(recipient_public_key)
            data_out["decryption_key"] = Binary(rsa_public_key.encrypt(data_out["decryption_key"], K=None)[0]) #K is ignored, but needed for compatibility

            data_in = self.requestResponse(dict(
                question = "Share?",
                data = data_out
            ))
            if data_in['success']:
                self.statusSignalForMain.emit(("Your item was sent", "good"))
            else:
                #print "sh"+data_in["reason"]
                self.statusSignalForMain.emit((data_in["reason"], "warn"))

        if question == "Update?":
                    
            container_name = data_out["container_name"]

            self.ensureContainerUpload(container_name)

            self.statusSignalForMain.emit(("Updating clip to server", "sync"))

            data_in = self.requestResponse(send)

            if data_in["success"]:
                 self.statusSignalForMain.emit(("Updated", "good"))
            else:
                #print "upd"+data_in["reason"]
                self.statusSignalForMain.emit((data_in["reason"], "warn"))

        elif question=="Delete?":

            self.statusSignalForMain.emit(("Deleting", "trash"))

            data_in = self.requestResponse(send)

            if data_in["success"] == True:
                LOG.debug("DELETE!")
                self.statusSignalForMain.emit(("Deleted from server", "good"))
            else:
                #print "del"+data_in["reason"]
                self.statusSignalForMain.emit((data_in["reason"], "warn"))
                    
        elif question=="Star?":
        
            self.statusSignalForMain.emit(("Adding to bookmarks", "star"))
            data_in = self.requestResponse(send)
            
            if data_in["success"]:
                self.statusSignalForMain.emit(("Added to your bookmarks!", "good"))
            else:
                #print "star"+data_in["reason"]
                self.statusSignalForMain.emit((data_in["reason"], "warn"))

        elif question=="Contacts?": #change to set_contacts?
            
            data_in = self.requestResponse(send)
            
            self.closeWaitDialogSignalForMain.emit(data_in)

        elif question=="Invite?":
            
            data_in = self.requestResponse(send)

            self.closeWaitDialogSignalForMain.emit(data_in)
            
        elif question =="Accept?":
            
            data_in = self.requestResponse(send)
            
            self.closeWaitDialogSignalForMain.emit(data_in)
            
