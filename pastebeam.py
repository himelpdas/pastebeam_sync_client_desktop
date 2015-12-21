#--coding: utf-8 --

from gevent import monkey; monkey.patch_all()

#from PySide import QtGui, QtCore

from parallel import *

from window import *

import platform, distutils.dir_util, distutils.errors, distutils.file_util #distutil over shututil http://stackoverflow.com/questions/15034151/copy-directory-contents-into-a-directory-with-python #import error on linux http://stackoverflow.com/questions/19097235/backing-up-copying-an-entire-folder-tree-in-batch-or-python

from QtSingleApplication import QtSingleApplication


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
        self.init_clipboard()

        self.singleton.messageReceived.connect(lambda msg: self.tray_icon.restore())

        self.ws_worker = WebsocketWorker(self)
        self.initWorker()

        self.contacts_list = []
        self.update_contacts_list_signal.connect(self.set_contacts_list)
        self.show_settings_dialog_signal.connect(lambda:SettingsDialog.show(self))


    def set_contacts_list(self, contacts_list):
        self.contacts_list = contacts_list

    def on_contacts_list_incoming(self, contacts_list):
        self.set_contacts_list(contacts_list)

    def initWorker(self):
        self.ws_worker.incoming_clip_signal_for_main.connect(self.on_incoming_slot)
        self.ws_worker.set_clip_signal_for_main.connect(self.on_set_new_clip_slot)
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


    def init_clipboard(self):
        self.previous_hash = {}

        self.clipboard = self.app.clipboard() #clipboard is in the QtGui.QApplication class as a static (class) attribute. Therefore it is available to all instances as well, ie. the app instance.#http://doc.qt.io/qt-5/qclipboard.html#changed http://codeprogress.com/python/libraries/pyqt/showPyQTExample.php?index=374&key=PyQTQClipBoardDetectTextCopy https://www.youtube.com/watch?v=nixHrjsezac
        self.clipboard.dataChanged.connect(self.on_clip_change_slot) #datachanged is signal, doclip is slot, so we are connecting slot to handle signal


    def on_clip_change_slot(self):
        #test if identical

        self.on_set_status_slot(("Waiting for change", "scan"))
        
        mimeData = self.clipboard.mimeData()
        if "PyQt4" in QtGui.__name__:
            variant = QtCore.QVariant.ByteArray
            retrieved = str(mimeData.retrieveData("__pastebeam__", variant).toByteArray())
            pastebeam_mime = json.loads(retrieved or "{}")  #unicode is preferred type to return... #USE PYTHON TYPES INSTEAD OF QVARIANT #http://stackoverflow.com/questions/24566940/no-qvariant-attributes
        else:
            pastebeam_mime = json.loads(str(mimeData.retrieveData("__pastebeam__", unicode) or "{}"))  #unicode is preferred type to return... #USE PYTHON TYPES INSTEAD OF QVARIANT #http://stackoverflow.com/questions/24566940/no-qvariant-attributes
        block_detection = pastebeam_mime.get("block_detection")
        if block_detection:
            # prevents redundant updating when clip is incomming from another device, no need to update to server what was just received
            return

        prev = self.previous_hash #image.bits() crashes with OneNote large image copy

        if mimeData.hasImage():
            #image = pmap.toImage() #just like wxpython do not allow this to del, or else .bits() will crash
            if "PyQt4" in QtGui.__name__:
                variant = mimeData.imageData()
                image   = variant.toPyObject()
                size = image.size()
                width = size.width()
                height = size.height()
                length = width * height * 3
                sip = image.bits()  # delete bits?  # returns a sip.voidptr object which is meant to reduce copying and directly access memory http://pyqt.sourceforge.net/Docs/sip4/python_api.html#sip.voidptr
                bits = sip.asarray(length)  # define the array's length, which we know is 3 * length * width of a bitmap
            else:
                image = mimeData.imageData()
                bits = image.bits()

            try: #None.bits attribute error here can cause a freeze
                hash = format(hash128(bits), "x") ##http://stackoverflow.com/questions/16414559/trying-to-use-hex-without-0x #we want the large image out of memory asap, so just take a hash and gc collect the image
            except AttributeError:
                return

            LOG.info("Main: on_clip_change_slot: mimeData.hasImage: hash:%s, prev:%s"%(hash, prev))
            if hash == prev:
                #self.on_set_status_slot(("image copied","good"))
                return
                
            #secure_hash = hashlib.new("ripemd160", hash + "ACCOUNT_SALT").hexdigest() #use pdkbf2 #to prevent rainbow table attacks of known files and their hashes, will also cause decryption to fail if file name is changed
            img_file_name = "%s.bmp"%hash
            img_file_path = os.path.join(CONTAINER_DIR, img_file_name)
            image.save(img_file_path) #change to or compliment upload
                
            pmap = QtGui.QPixmap(image) #change to pixmap for easier image editing than Qimage
            pmap = PixmapThumbnail(pmap, 240)
            
            device= QtCore.QBuffer() #is an instance of QtGui.QIODevice, which is accepted by image.save()
            pmap.thumbnail.save(device, "PNG") # writes image into the in-memory container, rather than a file name
            _bytearray = device.data() #get the buffer itself
            bytestring = _bytearray.data() #copy the full string
            
            info = dict(w=pmap.original_w, h=pmap.original_h, mp="%d.02"%(pmap.original_w*pmap.original_h/1000000.0), mb="%d.1"%(pmap.original_w*pmap.original_h*3/1024**2) )
            clip_display = dict(
                info=info,
                thumb = Binary(bytestring)  #Use BSON Binary to prevent UnicodeDecodeError: 'utf8' codec can't decode byte 0xeb in position 0: invalid continuation byte
            )
            
            prepare = dict(
                file_names = [img_file_name],
                clip_display = clip_display,
                clip_type = "screenshot",
            )

        elif mimeData.hasHtml():
            if "PyQt4" in QtGui.__name__:
                qstring = mimeData.html()  # QString
                html = unicode(qstring)  # convert to Unicode
                qstring = mimeData.text()
                text = unicode(qstring or "<Rich Text Data>")
            else:
                html = mimeData.html()  # already Unicode (Python representation, different on each OS)
                text = (mimeData.text() or "<Rich Text Data>")

            hash = format(hash128(html.encode("utf8")), "x")  # UTF-8 is standardized and OS independant. Must encode before storing to disk # http://stackoverflow.com/questions/22149/unicode-vs-utf-8-confusion-in-python-django
            
            LOG.info("Main: on_clip_change_slot: mimeData.hasImage: hash:%s, prev:%s"%(hash, prev))
            if hash == prev:
                #self.on_set_status_slot(("data copied","good"))
                return
            
            preview = cgi.escape(text) #crashes with big data
            #preview = self.truncateTextLines(preview)
            preview = self.anchor_urls(preview)
                        
            html_file_name = "%s.json"%hash
            html_file_path = os.path.join(CONTAINER_DIR,html_file_name)
            
            with open(html_file_path, 'w') as html_file:
                html_and_text = json.dumps({"html_and_text":{
                    "html":html,
                    "text":text
                }})
                html_file.write(html_and_text.encode("utf8"))
            
            prepare = dict(
                file_names = [html_file_name],
                clip_display = preview,
                clip_type = "html",
            )
            
        elif mimeData.hasText() and not mimeData.hasUrls(): #linux appears to provide text for files, so make sure it is not a file or else this will overrie it
            if "PyQt4" in QtGui.__name__:
                qstring = mimeData.text()
                original = unicode(qstring)
            else:
                original = mimeData.text()

            hash = format(hash128(original.encode("utf8")), "x")
            
            LOG.info("Main: on_clip_change_slot: mimeData.hasText: hash:%s, prev:%s"%(hash, prev))
            if hash == prev:
                #self.on_set_status_slot(("text copied","good"))
                return
            
            preview = cgi.escape(original) #prevent html from styling in qlabel
            preview = self.truncateTextLines(preview)
            preview = self.anchor_urls(preview)
                        
            text_file_name = "%s.txt"%hash
            text_file_path = os.path.join(CONTAINER_DIR,text_file_name)
            
            with open(text_file_path, 'w') as text_file:
                text_file.write(original.encode("utf8"))
            
            prepare = dict(
                file_names = [text_file_name],
                clip_display = preview,
                clip_type = "text",
            )

        elif mimeData.hasUrls():
            is_files = []
            for each in mimeData.urls():
                is_files.append(each.isLocalFile())
            if not (is_files and all(is_files) ):
                return

            os_file_paths_new = []
            
            for each in self.clipboard.mimeData().urls():
                if "PyQt4" in QtGui.__name__:
                    each_path = unicode(each.path())
                each_path = each_path[(1 if SYSTEM == "Windows" else 0):] #urls() returns /c://...// in windows, [1:] removes the starting /, not sure how this will affect *NIXs
                #if os.name=="nt":
                #    each_path = each_path.encode(sys.getfilesystemencoding()) #windows uses mbcs encoding, not utf8 like *nix, so something like a chinese character will result in file operations raising WindowsErrors #http://stackoverflow.com/questions/10180765/open-file-with-a-unicode-filename
                standardized_path = os.path.abspath(each_path) #abspath is needed to bypass symlinks in *NIX systems, also guarantees slashes are correct (C:\\...) for windows
                os_file_paths_new.append(standardized_path)
            
            os_file_paths_new.sort()
            
            try:
                os_file_sizes_new = map(lambda each_os_path: getFolderSize(each_os_path, max=self.max_file_size) if os.path.isdir(each_os_path) else os.path.getsize(each_os_path), os_file_paths_new)
            except ZeroDivisionError:
                LOG.error("Main: on_clip_change_slot: mimeData.hasUrls: os_file_sizes_new")
                return
            
            if sum(os_file_sizes_new) > self.max_file_size:
                #self.sb.toggleStatusIcon(msg='Files not uploaded. Maximum files size is 50 megabytes.', icon="bad")
                self.on_set_status_slot(("Files bigger than 50MB", "warn"))
                LOG.error("Main: on_clip_change_slot: mimeData.hasUrls: sum(os_file_sizes_new) > self.max_file_size")
                return #upload error clip
                            
            os_file_hashes_new = set([])
            
            os_file_names_new = []
            display_file_names =[]

            def _keep_ui_alive():
                """calling this at the rate that os.walk would will crash QT, this prevents that."""
                if once_every_second.check():
                    self.app.processEvents()  # YIELDS TO MAINLOOP # SIMILAR TO WX.YIELD # http://stackoverflow.com/questions/12410433/forcing-the-qt-gui-to-update-before-entering-a-separate-function
            
            for each_path in os_file_paths_new:
                _keep_ui_alive()
                each_file_name = os.path.basename(each_path) #instead of os.path.split(each_path)[1]

                os_file_names_new.append(each_file_name)

                if os.path.isdir(each_path):

                    display_file_names.append(each_file_name+" (%s things inside)"%len(os.listdir(each_path))+"._folder")

                    os_folder_hashes = []
                    for dirName, subdirList, fileList in os.walk(each_path, topdown=False):
                        _keep_ui_alive()
                        #subdirList = filter(...) #filer out any temp or hidden folders
                        for fname in fileList:
                            _keep_ui_alive()
                            if fname.upper() not in self.file_ignore_list: #DO NOT calculate hash for system files as they are always changing, and if a folder is in clipboard, a new upload may be initiated each time a system file is changed
                                each_sub_path = os.path.join(dirName, fname)
                                with open(each_sub_path, 'rb') as each_sub_file:
                                    each_relative_path = each_sub_path.split(each_path)[1].replace("\\", "/") #windows and *nix use different slashes, therefore different hashes, use one type of slash #c:/python27/lib/ - c:/python27/lib/bin/abc.pyc = bin/abc.pyc
                                    each_relative_hash = each_relative_path + hex(hash128( each_sub_file.read())) #WARNING- some files like thumbs.db constantly change, and therefore may cause an infinite upload loop. Need an ignore list.
                                    os_folder_hashes.append(each_relative_hash) #use relative path+filename and hash so that set does not ignore two idenitcal files in different sub-directories. Why? let's say bin/abc.pyc and usr/abc.pyc are identical, without the aforementioned system, a folder with just bin/abc.pyc will yield same hash as bin/abc.pyc + usr/abc.pyc, not good.

                    each_file_name = os.path.basename(each_path)
                    os_folder_hashes.sort() #sort so hash will be consistent
                    each_data = "".join(os_folder_hashes) #whole folder hash

                else: #single file

                    display_file_names.append(each_file_name)

                    with open(each_path, 'rb') as each_file:
                        each_file_name = os.path.basename(each_path)
                        each_data = each_file.read() #update status

                os_file_hashes_new.add(hash128(each_file_name.encode("utf8")) + hash128(each_data) ) #http://stackoverflow.com/questions/497233/pythons-os-path-choking-on-hebrew-filenames #append the hash for this file #use filename and hash so that set does not ignore copies of two idenitcal files (but different names) in different directories #also hash filename as this can be a security issue when stored serverside

            checksum = format(sum(os_file_hashes_new), "x")
            if prev == checksum:  #checks to make sure if name and file are the same
                LOG.error("Main: on_clip_change_slot: mimeData.hasUrls: prev == checksum")
                #self.on_set_status_slot(("File%s copied" % ("s" if len(os_file_names_new) > 1 else "") , "good"))
                return
            else:
                hash = checksum

            #copy files to temp. this is needed
            for each_new_path in os_file_paths_new:
                try:
                    if os.path.isdir(each_new_path):
                        distutils.dir_util.copy_tree(each_new_path, os.path.join(CONTAINER_DIR, os.path.split(each_new_path)[1] ) )
                    else:
                        distutils.file_util.copy_file(each_new_path, CONTAINER_DIR )
                except distutils.errors.DistutilsFileError:
                    #show error
                    LOG.error("Main: on_clip_change_slot: mimeData.hasUrls: File %s already exists" % each_new_path)
                    pass #MUST PASS since file may already be there.

            prepare = dict(
                file_names = os_file_names_new,
                clip_display = display_file_names,
                clip_type = "files",
            )

        else:
            self.on_set_status_slot(("The item in your clipboard is incompatible and can't be synced", "warn"))
            return

        prepare["hash"]= hash

        try:
            container_name = self.panel_tab_widget.get_matching_containers_for_hash(hash).next()
            prepare["container_name"] = container_name  # only need first
        except StopIteration:
            pass

        async_process = dict(question="Update?", data=prepare)

        self.outgoing_signal_for_worker.emit(async_process)

        self.previous_hash = hash
        #image.destroy()


    def streaming_download_callback(self, progress):
        self.on_set_status_slot(("Downloading %s" % progress["percent_done"], "download"))


    def block_clip_change_detection(func):
        """When incoming, this will invoke dataChanged, which will in turn invoke a push, therefore a race condition
        will occur with multiple devices. This decorator will block redundant reupload from clipboard.dataChanged"""
        def closure(self, clip_dict):
            LOG.info("on_set_new_clip_slot: block_clip_change_detection: clip_dict: %s" % clip_dict)

            new_clip, block_detection = clip_dict["new_clip"], clip_dict["block_clip_change_detection"]

            #http://stackoverflow.com/questions/5339062/python-pyside-internal-c-object-already-deleted
            #mimedata should be held in a parent object or self
            #http://doc.qt.io/qt-4.8/qmimedata.html
            mimeData = QtCore.QMimeData()  # NEED the self to prevent garbage collection
            pastebeam_mime = {'previous_id':new_clip["_id"]}  # not needed, but good to know. # _id MUST exist, so enforce it
            if block_detection:
                pastebeam_mime["block_detection"] = True
                mimeData.setData("__pastebeam__", json.dumps(pastebeam_mime))
            try:
                func(self, new_clip, mimeData)
                # self.previous_hash = new_clip["hash"]  # so that we don't get a redundant on_clip_change_slot, and a hit to the server. needed since an incoming will not set self.previous_hash
            except RuntimeError, e:  # sometimes mimeData can be garbage collected despite passing it to the parent object to prevent GC
                LOG.error(e) # todo - error report
            except tarfile.ReadError as e:
                # when decryption fails, tarfile is corrupt and raises: tarfile.ReadError: file could not be opened successfully
                LOG.error("Main: on_set_new_clip_slot: block_clip_change_detection: tarfile: " + e[0])
                self.on_set_status_slot(("Decryption failed. Current password is not compatible with this item", "bad"))
            except IOError:
                LOG.error("Main: on_set_new_clip_slot: block_clip_change_detection: Possibly in the middle of downloading a container of a clip, while another client double-clicks the same clip, so extracted tarfile fails with (from tarfile.py): IOError: CRC check failed 0x9e952259 != 0x3b63bdc0L")
            except ValueError:
                LOG.error("Main: on_set_new_clip_slot: block_clip_change_detection: Missing or corrupt container from server")
                self.on_set_status_slot(("Decryption failed. Item data from server is missing or corrupt", "bad")) #ie. server returned a 404.html document
            else:
                self.on_set_status_slot(("Decrypted an item", "good"))
        return closure


    @block_clip_change_detection
    def on_set_new_clip_slot(self, new_clip, mimeData):  # happens when new incoming clip or when user double clicks an item

        container_name = new_clip["container_name"]
        clip_type = new_clip["clip_type"]
        system = new_clip["system"]
        
        #downloading modal
        download_container_if_not_exist(new_clip, self.streaming_download_callback)  # TODO - show error message if download not found on server

        self.on_set_status_slot(("Decrypting", "unlock"))
        if system == "share":
            ciphertext = new_clip["decryption_key"]
            password = self.rsa_private_key.decrypt(ciphertext) #this is set on logon guaranteed!
            print password
        else:
            password = settings.account.get("password")

        with encompress.Encompress(password = password, directory = CONTAINER_DIR, container_name_decrypt=container_name) as file_paths_decrypt:

            if clip_type == "html":

                clip_file_path = file_paths_decrypt[0]

                with open(clip_file_path, 'r') as clip_file:

                    clip_json = json.loads(clip_file.read())  # json handles encode and decode of UTF8

                    clip_text = clip_json["html_and_text"]["text"]
                    clip_html = clip_json["html_and_text"]["html"]

                    LOG.info("Main: on_set_new_clip_slot: files: mimeData.setHtml: %s" % clip_html)
                    mimeData.setText(clip_text)  # set text cannot automatically truncate html (or rich text tags) like with mimeData.text(). This is probably due to the operating system providing both text and html, and it's not Qt's concern. So I decided to store getText on json file and setText here.
                    mimeData.setHtml(clip_html)


            if clip_type == "text":

                clip_file_path = file_paths_decrypt[0]

                with open(clip_file_path, 'r') as clip_file:

                    clip_text = clip_file.read().decode("utf8")  # http://stackoverflow.com/questions/6048085/python-write-unicode-text-to-a-text-file #needed to keep conistant hash, or else inifnite upload/update loop will occur

                    LOG.info("Main: on_set_new_clip_slot: files: mimeData.setText: %s" % clip_text)
                    mimeData.setText(clip_text)


            if clip_type == "screenshot":

                clip_file_path = file_paths_decrypt[0]

                image = QtGui.QImage(clip_file_path)

                LOG.info("Main: on_set_new_clip_slot: files: mimeData.setImageData: %s" % image)
                mimeData.setImageData(image)


            if clip_type == "files":

                urls = []

                for each_path in file_paths_decrypt:

                    QUrl = QtCore.QUrl()
                    #QUrl.setUrl(each_path)
                    #QUrl.setPath(each_path)
                    QUrl = QUrl.fromLocalFile(each_path)  # Returns a QUrl representation of localFile #http://stackoverflow.com/questions/6062382/pyqt-copy-file-to-clipboard
                    #QUrl.toEncoded()
                    urls.append(QUrl)

                LOG.info("Main: on_set_new_clip_slot: files: mimeData.setUrls: %s" % urls)
                mimeData.setUrls(urls)

            if not self.clipboard.ownsClipboard():  # solves issue #14, a silent error QClipboard::setMimeData: Failed to set data on clipboard (). happens when another program takes clipboard, so we re-init here. doesn't seem to be needed when reading clipboard
                self.init_clipboard()
            self.clipboard.setMimeData(mimeData)


    @staticmethod
    def truncateTextLines(txt, max_lines=15):
        line_count = txt.count("\n")
        if line_count <= max_lines:
            return txt
        txt_split = txt.split("\n")
        line_diff = line_count-max_lines
        txt_split = txt_split[:max_lines] + ["<span style='color:red'>...", "... %s line%s not shown"%(line_diff, "s" if line_diff > 1 else ""), "...</span>"] + txt_split[-1:] #equal to [txt_split[-1]]
        txt = "\n".join(txt_split)
        return txt
    
    @staticmethod
    def anchor_urls(txt):
        found_urls = map(lambda each: each[0], GRUBER_URLINTEXT_PAT.findall(txt))
        for each_url in found_urls:
            txt = txt.replace(each_url, "<a href='{url}'>{url}</a>".format(url=each_url.replace("&amp;", "&") ) )  # unescape &
        return txt
        
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