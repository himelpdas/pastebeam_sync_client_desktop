from gevent import monkey; monkey.patch_all(thread=False)  # thread MUST equal False or else unexpected behavior will occur with multiprocess

from pastebeam_application import *

import sys, multiprocessing
from multiprocessing.queues import SimpleQueue
import itertools


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
                break
            self.status_signal.emit(status)


class Consumer(Main):

    def __init__(self, app, clip_change_queue, set_clip_queue, status_queue, kill_event, previous_hash, *args, **kwargs):
        LOG.info("Pastebeam: Consumer: __init__: " + multiprocessing.current_process().name)

        app_id = '3B9D38D3-AAA6-476D-97CB-E547F623B96E'
        singleton = QtSingleApplication(app_id, sys.argv)
        if singleton.isRunning():
            singleton.sendMessage("restore")
            #sys.exit(0)  # http://stackoverflow.com/questions/12712360/qtsingleapplication-for-pyside-or-pyqt

        super(self.__class__, self).__init__(app, singleton, *args, **kwargs)

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

    def closeEvent(self, close_event):
        self.kill_event.set()
        self.clip_change_queue.put_nowait(False)
        self.status_queue.put_nowait(False)
        #self.app.exit()
        close_event.accept()

class ProducerSetClipboardQueueListenerThread(QtCore.QThread):

    clipboard_set_signal = QtCore.pyqtSignal(dict)

    def __init__(self, kill_event, set_clip_queue, *args, **kwargs):
        LOG.info("Pastebeam: Consumer: ProducerSetClipboardQueueListenerThread " + multiprocessing.current_process().name)

        self.set_clip_queue = set_clip_queue
        self.kill_event = kill_event

        super(self.__class__, self).__init__(*args, **kwargs)

    def run(self):
        while 1:
            set_clip = self.set_clip_queue.get()  # blocks
            print "d-clicked!!!"
            if set_clip is False or self.kill_event.is_set():  # poison pill technique  # there slight chance there is a positive set_clip and a kill_event.is_set at the same time, so check for kill to prevent wasted time
                break
            self.clipboard_set_signal.emit(set_clip)

class ProducerKillQueueListenerThread(QtCore.QThread):

    kill_producer_signal = QtCore.pyqtSignal()

    def __init__(self, kill_event, *args, **kwargs):
        LOG.info("Pastebeam: Consumer: ProducerKillQueueListenerThread " + multiprocessing.current_process().name)

        self.kill_event = kill_event

        super(self.__class__, self).__init__(*args, **kwargs)

    def run(self):
        self.kill_event.wait()
        self.kill_producer_signal.emit()



class Producer(QtGui.QMainWindow):
    kill_ms = 1000 * 5
    timeout = kill_ms * 1.5
    def __init__(self, app, clip_change_queue, set_clip_queue, status_queue, kill_event, previous_hash, *args, **kwargs):
        LOG.info("Pastebeam: Producer: __init__: " + multiprocessing.current_process().name)

        self.next_producer = kwargs.pop("next_producer")  # get rid of next_producer or else super init will raise TypeError for unknown kwarg

        super(self.__class__, self).__init__(*args, **kwargs)

        self.app = app
        self.clip_change_queue = clip_change_queue
        self.set_clip_queue = set_clip_queue
        self.kill_event = kill_event
        self.status_queue = status_queue
        self.previous_hash = previous_hash

        self.clipboard = app.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_data_changed)

        self.kill_event_thread = ProducerKillQueueListenerThread(self.kill_event)
        self.kill_event_thread.kill_producer_signal.connect(self.terminate)
        self.kill_event_thread.start()

        self.set_clip_thread  = ProducerSetClipboardQueueListenerThread(self.kill_event, self.set_clip_queue)
        self.set_clip_thread.clipboard_set_signal.connect(self.on_set_new_clip_slot)
        self.set_clip_thread.start()

        self.kill_after(self.kill_ms)
        print multiprocessing.current_process().name

    def terminate(self):
        self.next_producer.set()
        LOG.info("Pastebeam: Producer: terminate")
        self.set_clip_queue.put_nowait(False)
        #self.app.exit()  # http://stackoverflow.com/questions/8026101/correct-way-to-quit-a-qt-program
        self.close()

    def kill_after(self, ms):
        self.timer  = QtCore.QTimer(self)
        self.timer.setInterval(ms)  # Throw event timeout with an interval of 1000 milliseconds
        self.timer.timeout.connect(self.terminate)  # this ensures clipboard stays alive
        self.timer.start()

    def on_clipboard_data_changed(self):
        #test if identical

        self.status_queue.put_nowait(("Waiting for clipboard to change", "scan"))

        mimeData = self.clipboard.mimeData()
        if "PyQt4" in QtGui.__name__:
            variant = QtCore.QVariant.ByteArray
            retrieved = unicode(mimeData.retrieveData("__pastebeam__", variant).toByteArray())
            pastebeam_mime = json.loads(retrieved or "{}")  #unicode is preferred type to return... #USE PYTHON TYPES INSTEAD OF QVARIANT #http://stackoverflow.com/questions/24566940/no-qvariant-attributes
        else:
            pastebeam_mime = json.loads(unicode(mimeData.retrieveData("__pastebeam__", unicode) or "{}"))  #unicode is preferred type to return... #USE PYTHON TYPES INSTEAD OF QVARIANT #http://stackoverflow.com/questions/24566940/no-qvariant-attributes
        block_detection = pastebeam_mime.get("block_detection")
        if block_detection:
            # prevents redundant updating when clip is incomming from another device, no need to update to server what was just received
            return

        prev = self.previous_hash.value #image.bits() crashes with OneNote large image copy

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
                hash_long = hash128(bits)
                hash_hex = format(hash_long, "x") ##http://stackoverflow.com/questions/16414559/trying-to-use-hex-without-0x #we want the large image out of memory asap, so just take a hash and gc collect the image
            except AttributeError:
                return

            LOG.info("Main: on_clip_change_slot: mimeData.hasImage: hash:%s, prev:%s"%(hash_hex, prev))
            if hash_long == prev:
                #self.status_queue.put_nowait(("image copied","good"))
                return

            #secure_hash = hashlib.new("ripemd160", hash + "ACCOUNT_SALT").hexdigest() #use pdkbf2 #to prevent rainbow table attacks of known files and their hashes, will also cause decryption to fail if file name is changed
            img_file_name = "%s.bmp"%hash_hex
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
            
            hash_long = hash128(html.encode("utf8"))
            hash_hex = format(hash_long, "x")  # UTF-8 is standardized and OS independant. Must encode before storing to disk # http://stackoverflow.com/questions/22149/unicode-vs-utf-8-confusion-in-python-django

            LOG.info("Main: on_clip_change_slot: mimeData.hasHtml: hash:%s, prev:%s"%(hash_hex, prev))
            if hash_long == prev:
                #self.status_queue.put_nowait(("data copied","good"))
                return

            preview = self.prepare_text_preview(text)

            html_file_name = "%s.json" % hash_hex
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

            hash_long = hash128(original.encode("utf8"))
            hash_hex = format(hash_long, "x")  # UTF-8 is standardized and OS independant. Must encode before storing to disk # http://stackoverflow.com/questions/22149/unicode-vs-utf-8-confusion-in-python-django

            LOG.info("Main: on_clip_change_slot: mimeData.hasText: hash:%s, prev:%s"%(hash_hex, prev))
            if hash_hex == prev:
                #self.status_queue.put_nowait(("text copied","good"))
                return

            preview = self.prepare_text_preview(original)

            text_file_name = "%s.txt"%hash_hex
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
                self.status_queue.put_nowait(("Files bigger than 50MB", "warn"))
                LOG.error("Main: on_clip_change_slot: mimeData.hasUrls: sum(os_file_sizes_new) > self.max_file_size")
                return #upload error clip

            os_file_hashes_new = set([])

            os_file_names_new = []
            display_file_names =[]

            for each_path in os_file_paths_new:
                each_file_name = os.path.basename(each_path) #instead of os.path.split(each_path)[1]

                os_file_names_new.append(each_file_name)

                if os.path.isdir(each_path):

                    display_file_names.append(each_file_name+" (%s things inside)"%len(os.listdir(each_path))+"._folder")

                    os_folder_hashes = []
                    for dirName, subdirList, fileList in os.walk(each_path, topdown=False):
                        #subdirList = filter(...) #filer out any temp or hidden folders
                        for fname in fileList:
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
                        each_data = each_file.read() #update status_queue

                os_file_hashes_new.add(hash128(each_file_name.encode("utf8")) + hash128(each_data) ) #http://stackoverflow.com/questions/497233/pythons-os-path-choking-on-hebrew-filenames #append the hash for this file #use filename and hash so that set does not ignore copies of two idenitcal files (but different names) in different directories #also hash filename as this can be a security issue when stored serverside

            hash_long = sum(os_file_hashes_new)
            if prev == hash_long:  #checks to make sure if name and file are the same
                LOG.error("Main: on_clip_change_slot: mimeData.hasUrls: prev == checksum")
                #self.status_queue.put_nowait(("File%s copied" % ("s" if len(os_file_names_new) > 1 else "") , "good"))
                return
            else:
                hash_hex = format(hash_long, "x")

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
            self.status_queue.put_nowait(("The item in your clipboard is incompatible and can't be synced", "warn"))
            return

        prepare["hash"] = hash_hex

        async_process = dict(question="Update?", data=prepare)

        #self.outgoing_signal_for_worker.emit(async_process)
        self.clip_change_queue.put_nowait(async_process)

        self.previous_hash.value = hash_long
        #image.destroy()

    def prepare_text_preview(self, text):
        preview = cgi.escape(text) #crashes with big data
        #preview = self.truncateTextLines(preview)
        preview = self.anchor_urls(preview)
        try:
            preview = pygments.highlight(preview, pygments.lexers.guess_lexer(preview), pygments.formatters.HtmlFormatter(noclasses=True))
        except pygments.util.ClassNotFound:
            pass
        return preview

    @staticmethod
    def anchor_urls(txt):
        found_urls = map(lambda each: each[0], GRUBER_URLINTEXT_PAT.findall(txt))
        for each_url in found_urls:
            txt = txt.replace(each_url, "<a href='{url}'>{url}</a>".format(url=each_url.replace("&amp;", "&") ) )  # unescape &
        return txt

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
                self.status_queue.put_nowait(("Decryption failed. Current password is not compatible with this item", "bad"))
            except IOError:
                LOG.error("Main: on_set_new_clip_slot: block_clip_change_detection: Possibly in the middle of downloading a container of a clip, while another client double-clicks the same clip, so extracted tarfile fails with (from tarfile.py): IOError: CRC check failed 0x9e952259 != 0x3b63bdc0L")
            except ValueError:
                LOG.error("Main: on_set_new_clip_slot: block_clip_change_detection: Missing or corrupt container from server")
                self.status_queue.put_nowait(("Decryption failed. Item data from server is missing or corrupt", "bad")) #ie. server returned a 404.html document
            else:
                self.status_queue.put_nowait(("Decrypted an item", "good"))
        return closure


    def streaming_download_callback(self, progress):
        self.status_queue.put_nowait(("Downloading %s" % progress["percent_done"], "download"))


    @block_clip_change_detection
    def on_set_new_clip_slot(self, new_clip, mimeData):  # happens when new incoming clip or when user double clicks an item

        container_name = new_clip["container_name"]
        clip_type = new_clip["clip_type"]
        system = new_clip["system"]

        #downloading modal
        download_container_if_not_exist(new_clip, self.streaming_download_callback)  # TODO - show error message if download not found on server

        self.status_queue.put_nowait(("Decrypting", "unlock"))
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

            #if self.clipboard.ownsClipboard():  # TODO - move to Multiproc
            self.clipboard.setMimeData(mimeData)


def parallel_worker(role, clip_change_queue, set_clip_queue, status_queue, kill_event, previous_hash,
                    **unshared):
    #clip_change_queue, kill_event, role = args
    app = QtGui.QApplication(sys.argv)
    window = role(app, clip_change_queue, set_clip_queue, status_queue, kill_event, previous_hash,
                  **unshared)
    app.exec_()


if __name__ == "__main__":
    #manager = multiprocessing.Manager()  # Done via networking. GEVENT fucks this up. Can't use patch_all(socket=False) because we need requests and urllib patched
    clip_change_queue = multiprocessing.Queue()  # Gevent fucks this up!! USE patch_all(thread=False), Also use SimpleQueue as gevent patches multiprocessing.Queue()
    set_clip_queue = multiprocessing.Queue()  # This will cause set_clup_queue.get() to hang without a context switch
    status_queue = multiprocessing.Queue()
    kill_event = multiprocessing.Event()
    next_producer = multiprocessing.Event()
    previous_hash = multiprocessing.Value("d",long(0))

    #args = args_generator()
    args = (clip_change_queue, set_clip_queue, status_queue, kill_event, previous_hash)
    args = itertools.chain(itertools.repeat((Consumer,) + args, 1),  # 1 means repeat once
                           itertools.repeat((Producer,) + args)  # repeat infinite
                           )  # http://stackoverflow.com/questions/3211041/how-to-join-two-generators-in-python

    p = multiprocessing.Process(name="Consumer", target=parallel_worker, args=args.next())
    p.start()

    for i, each in enumerate(args):
        if kill_event.is_set():
            break
        next_producer.clear()
        q = multiprocessing.Process(name="Producer_%s" % i, target=parallel_worker, args=each,
                                    kwargs=dict(next_producer = next_producer))
        #q.daemon = True
        q.start()
        qpid = q.pid
        print "Starting " + unicode(qpid)
        next_producer.wait(timeout = Producer.timeout)
        print "Next was set terminating " + unicode(qpid)
        #q.terminate()