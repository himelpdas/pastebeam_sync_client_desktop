from functions import *

import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

import distutils.dir_util, distutils.errors, distutils.file_util #distutil over shututil http://stackoverflow.com/questions/15034151/copy-directory-contents-into-a-directory-with-python #import error on linux http://stackoverflow.com/questions/19097235/backing-up-copying-an-entire-folder-tree-in-batch-or-python

import pygments, pygments.lexers, pygments.formatters

import multiprocessing, tarfile, cgi

from spooky import hash32, hash128  # have to use hash32 because multiprocessing.Value("L",long(0)) max is 2**(8*4)

import encompress

from bson.binary import Binary

"""
We will use PySide to prevent Runtime Error "no access to protected functions or signals for objects not created in Python".
This is because QApplication.clipboard().mimeData().retrieveData() is a protected C++ function.
This only happens on Linux not Windows, probably because Windows does not have OS.fork()
"""

class ProducerSetClipboardQueueListenerThread(QtCore.QThread):

    clipboard_set_signal = QtCore.Signal(dict)

    def __init__(self, kill_event, set_clip_queue, *args, **kwargs):
        LOG.info("Pastebeam: Consumer: ProducerSetClipboardQueueListenerThread " + multiprocessing.current_process().name)

        self.set_clip_queue = set_clip_queue
        self.kill_event = kill_event

        super(self.__class__, self).__init__(*args, **kwargs)

    def run(self):
        while 1:
            set_clip = self.set_clip_queue.get()  # blocks  # is not writing, so should be thread safe
            if set_clip is False or self.kill_event.is_set():  # poison pill technique  # there slight chance there is a positive set_clip and a kill_event.is_set at the same time, so check for kill to prevent wasted time
                break
            self.clipboard_set_signal.emit(set_clip)

class ProducerKillQueueListenerThread(QtCore.QThread):

    kill_producer_signal = QtCore.Signal()

    def __init__(self, kill_event, *args, **kwargs):
        LOG.info("Pastebeam: Consumer: ProducerKillQueueListenerThread " + multiprocessing.current_process().name)

        self.kill_event = kill_event

        super(self.__class__, self).__init__(*args, **kwargs)

    def run(self):
        self.kill_event.wait()  # is not writing, so should be thread safe
        self.kill_producer_signal.emit()



class Producer(QtGui.QMainWindow):
    kill_ms = 1000 * 60 * 2
    timeout = kill_ms * 1.5
    file_ignore_list = map(lambda each: each.upper(), ["desktop.ini","thumbs.db",".ds_store", r"icon\r",".dropbox",".dropbox.attr"])
    max_file_size = 1024*1024*50

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
        #self.kill_event_thread.start()

        self.set_clip_thread  = ProducerSetClipboardQueueListenerThread(self.kill_event, self.set_clip_queue)
        self.set_clip_thread.clipboard_set_signal.connect(self.on_set_new_clip_slot)
        self.set_clip_thread.start()

        self.kill_after(self.kill_ms)
        print multiprocessing.current_process().name

    def terminate(self):
        LOG.info("Pastebeam: Producer: terminate")
        self.set_clip_queue.put(False)
        self.next_producer.set()
        #self.app.exit()  # http://stackoverflow.com/questions/8026101/correct-way-to-quit-a-qt-program
        self.close()  # i don't think it'll close the thread until the worker thread completes, hence why the processes don't lock up from corruption

    def kill_after(self, ms):
        self.timer  = QtCore.QTimer(self)
        self.timer.setInterval(ms)  # Throw event timeout with an interval of 1000 milliseconds
        self.timer.timeout.connect(self.terminate)  # this ensures clipboard stays alive
        self.timer.start()

    def on_clipboard_data_changed(self):
        #test if identical

        self.status_queue.put(("Waiting for clipboard to change", "scan"))

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

        print "NIGGER %s"%type(prev)

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
                hash_long = hash32(bits)
                hash_hex = format(hash_long, "x") ##http://stackoverflow.com/questions/16414559/trying-to-use-hex-without-0x #we want the large image out of memory asap, so just take a hash and gc collect the image
            except AttributeError:
                return

            LOG.info("Main: on_clip_change_slot: mimeData.hasImage: hash:%s, prev:%s"%(hash_hex, prev))
            if hash_long == prev:
                #self.status_queue.put(("image copied","good"))
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

            hash_long = hash32(html.encode("utf8"))
            hash_hex = format(hash_long, "x")  # UTF-8 is standardized and OS independant. Must encode before storing to disk # http://stackoverflow.com/questions/22149/unicode-vs-utf-8-confusion-in-python-django

            LOG.info("Main: on_clip_change_slot: mimeData.hasHtml: hash:%s, prev:%s"%(hash_hex, prev))
            if hash_long == prev:
                #self.status_queue.put(("data copied","good"))
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

            hash_long = hash32(original.encode("utf8"))
            hash_hex = format(hash_long, "x")  # UTF-8 is standardized and OS independant. Must encode before storing to disk # http://stackoverflow.com/questions/22149/unicode-vs-utf-8-confusion-in-python-django

            LOG.info("Main: on_clip_change_slot: mimeData.hasText: hash:%s, prev:%s"%(hash_long, prev))
            if prev == hash_long:
                #self.status_queue.put(("text copied","good"))
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
                self.status_queue.put(("Files bigger than 50MB", "warn"))
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
                                    each_relative_hash = each_relative_path + hex(hash32( each_sub_file.read())) #WARNING- some files like thumbs.db constantly change, and therefore may cause an infinite upload loop. Need an ignore list.
                                    os_folder_hashes.append(each_relative_hash) #use relative path+filename and hash so that set does not ignore two idenitcal files in different sub-directories. Why? let's say bin/abc.pyc and usr/abc.pyc are identical, without the aforementioned system, a folder with just bin/abc.pyc will yield same hash as bin/abc.pyc + usr/abc.pyc, not good.

                    each_file_name = os.path.basename(each_path)
                    os_folder_hashes.sort() #sort so hash will be consistent
                    each_data = "".join(os_folder_hashes) #whole folder hash

                else: #single file

                    display_file_names.append(each_file_name)

                    with open(each_path, 'rb') as each_file:
                        each_file_name = os.path.basename(each_path)
                        each_data = each_file.read() #update status_queue

                os_file_hashes_new.add(format(hash128(each_file_name.encode("utf8")) + hash128(each_data), "x") ) #http://stackoverflow.com/questions/497233/pythons-os-path-choking-on-hebrew-filenames #append the hash for this file #use filename and hash so that set does not ignore copies of two idenitcal files (but different names) in different directories #also hash filename as this can be a security issue when stored serverside
                # using hash128 to reduce collisions by increasing search space vs hash32
            hash_long = hash32("".join(os_file_hashes_new))
            if prev == hash_long:  #checks to make sure if name and file are the same
                LOG.error("Main: on_clip_change_slot: mimeData.hasUrls: prev == checksum")
                #self.status_queue.put(("File%s copied" % ("s" if len(os_file_names_new) > 1 else "") , "good"))
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
            self.status_queue.put(("The item in your clipboard is incompatible and can't be synced", "warn"))
            return

        prepare["hash"] = hash_hex

        async_process = dict(question="Update?", data=prepare)

        self.clip_change_queue.put(async_process)

        LOG.info("Pastebeam: Producer: on_clipboard_data_changed: hash_long = %s, prev = %s" % (hash_long, prev))
        self.previous_hash.value = hash_long

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
                self.status_queue.put(("Decryption failed. Current password is not compatible with this item", "bad"))
            except IOError:
                LOG.error("Main: on_set_new_clip_slot: block_clip_change_detection: Possibly in the middle of downloading a container of a clip, while another client double-clicks the same clip, so extracted tarfile fails with (from tarfile.py): IOError: CRC check failed 0x9e952259 != 0x3b63bdc0L")
            except ValueError:
                LOG.error("Main: on_set_new_clip_slot: block_clip_change_detection: Missing or corrupt container from server")
                self.status_queue.put(("Decryption failed. Item data from server is missing or corrupt", "bad")) #ie. server returned a 404.html document
            else:
                self.status_queue.put(("Decrypted an item", "good"))
        return closure


    def streaming_download_callback(self, progress):
        self.status_queue.put(("Downloading %s" % progress["percent_done"], "download"))


    @block_clip_change_detection
    def on_set_new_clip_slot(self, new_clip, mimeData):  # happens when new incoming clip or when user double clicks an item

        container_name = new_clip["container_name"]
        clip_type = new_clip["clip_type"]
        system = new_clip["system"]

        #downloading modal
        download_container_if_not_exist(new_clip, self.streaming_download_callback)  # TODO - show error message if download not found on server

        self.status_queue.put(("Decrypting", "unlock"))
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


class PixmapThumbnail():
    Px = 48

    def __init__(self, original_pmap, Px = None):
        if Px:
            self.Px = Px
        self.original_pmap = original_pmap
        self.original_w = self.original_h = self.thumbnail = self.is_landscape = None
        self.pixmap_thumbanail()

    def pixmap_thumbanail(self):
        self.original_w = self.original_pmap.width()
        self.original_h = self.original_pmap.height()
        is_square = self.original_w == self.original_h
        if not is_square:
            smallest_side = min(self.original_w, self.original_h)
            longest_side = max(self.original_w, self.original_h)
            shift = longest_side / 4.0
            self.is_landscape = self.original_w > self.original_h
            if self.is_landscape:
                x = shift
                y = 0
            else:
                x = 0
                y = shift
            crop = self.original_pmap.copy(x, y, smallest_side,
                                           smallest_side)  # PySide.QtGui.QPixmap.copy(x, y, width, height) #https://srinikom.github.io/pyside-docs/PySide/QtGui/QPixmap.html#PySide.QtGui.PySide.QtGui.QPixmap.copy
        else:
            crop = self.original_pmap
        self.thumbnail = crop.scaled(self.Px, self.Px, transformMode=QtCore.Qt.SmoothTransformation)
