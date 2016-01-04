# --coding: utf-8 --

import urlparse
import os, platform, requests

import logging
logging.basicConfig()
LOG = logging.getLogger("pastebeam")
LOG.setLevel(logging.DEBUG)

SYSTEM = platform.system()  # returns Windows, Darwin, Linux

import bson.json_util as json

import uuid, tempfile, datetime

import keyring

# DEFAULT_DOMAIN = "192.168.0.191"
# DEFAULT_DOMAIN = "192.168.0.12"
# DEFAULT_DOMAIN = "127.0.0.1"
DEFAULT_DOMAIN = "0.0.0.0"
DEFAULT_PORT = 8084

CONTAINER_DIR = os.path.join(tempfile.gettempdir(), u".pastebeam")  # tempfile.mkdtemp() #TODO- use tempfile.mkdtemp() when extracting container, as it guarantees other programs will not be able to intercept extracted file, see tempfile docs for more info
try:
    os.mkdir(CONTAINER_DIR)
except OSError:
    pass


def string_is_url(url):
    split_url = url.split()
    if len(url) < 2048 and len(
            split_url) == 1:  # make sure text is under 2048 (for performance), and make sure the text is continuous like a url should be
        if bool(urlparse.urlparse(split_url[0]).scheme in ['http', 'https', 'ftp', 'ftps', 'bitcoin',
                                                           'magnet']):  # http://stackoverflow.com/questions/25259134/how-can-i-check-whether-a-url-is-valid-using-urlparse
            return True
    return False


def getFolderSize(folder,
                  max=None):  # http://stackoverflow.com/questions/1392413/calculating-a-directory-size-using-python
    # recursively check folder size
    total_size = os.path.getsize(folder)
    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += getFolderSize(itempath)
        if max and total_size >= max:
            return float(
                "inf")  # 1024*1024*1024*1024 #http://stackoverflow.com/questions/7781260/how-can-i-represent-an-infinite-number-in-python
    return total_size


# See: http://daringfireball.net/2010/07/improved_regex_for_matching_urls
import re, urllib

GRUBER_URLINTEXT_PAT = re.compile(
    ur'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))')


def PRINT(label, data):
    print "\n%s: %s" % (label.capitalize(), data)


def URL(scheme, addr, port, *_args, **_vars):
    url = "{scheme}://{addr}:{port}/".format(scheme=scheme, addr=addr, port=port)
    if _args:
        args = "/".join(_args)
        url += args
    if _vars:
        url += "?"
        for key, value in _vars.items():
            url += "{key}={value}&".format(key=key, value=value)
        url = url[:-1]
    return url

class OnceEveryX():
    """
    Return True every interval. Prevents reuse of the same second, despite the frequency of calls to check()
    """
    def __init__(self, interval):
        self.interval = interval
        self.just_used = None
    def check(self,):
        second = datetime.datetime.now().second
        if second != self.just_used and second % self.interval == 0:
            self.just_used = second
            return True

once_every_second = OnceEveryX(1)

def download_container_if_not_exist(data, progress_callback=None):
    if not data.get("container_name"):
        return
    container_name = data["container_name"]
    container_path = os.path.join(CONTAINER_DIR, container_name)
    LOG.info("global: download_container_if_not_exist: %s" % container_path)

    if os.path.isfile(container_path):
        return container_path
    else:
        # TODO- show downloading file dialogue
        try:
            # urllib.urlretrieve(URL(arg="static/%s"%container_name,port=8084,scheme="http"), container_path)
            # urllib.URLopener().retrieve(URL("http", DEFAULT_DOMAIN, DEFAULT_PORT, "static", container_name), container_path) #http://stackoverflow.com/questions/1308542/how-to-catch-404-error-in-urllib-urlretrieve
            url = URL("http", DEFAULT_DOMAIN, DEFAULT_PORT, "static", container_name)
            get_file(url, container_path, progress_callback)
        except IOError:
            pass
        else:
            return container_path

def get_file(url, container_path, progress_callback=None,
            callback_frequency=55):  # 8192 bytes * 100 / 1024 / 1024 ~ every 0.8 mb it'll callback. Too quickly and app will CRASH!
    """http://stackoverflow.com/questions/16694907/how-to-download-large-file-in-python-with-requests-py"""
    if not progress_callback:  # no need to breakup the request into smaller bits for progress, so just use reliable urllib
        urllib.URLopener().retrieve(url, container_path)  # http://stackoverflow.com/questions/1308542/how-to-catch-404-error-in-urllib-urlretrieve
        return
    # progress report wanted so do progress callback will run once every <frequency>
    r = requests.get(url, stream=True)
    chunk_size = 8192
    file_size_now = file_size_original = int(r.headers['content-length'])
    with open(container_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=chunk_size):  # chunk in bytes
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()  # http://stackoverflow.com/questions/7127075/what-exactly-the-pythons-file-flush-is-doing #The first, flush, will simply write out any data that lingers in a program buffer to the actual file. Typically this means that the data will be copied from the program buffer to the operating system buffer.

                file_size_now -= chunk_size
                if once_every_second.check(): # FIXED- THIS IS PRONE TO CRASH IF INTERNET IS FAST, AS TOO MANY EMITS WILL OVERLOAD APP. MAKING IT TIME BASED WILL NOT CRASH!
                    downloaded = file_size_original - file_size_now

                    percent = float(downloaded) / file_size_original * 100.0
                    if percent > 100.0:
                        percent = 100.0
                    percent = "%.2f%%" % percent

                    progress = {
                        "remaining": file_size_now,
                        "downloaded": downloaded,
                        "percent_done": percent,
                    }

                    progress_callback(progress)


host_name = u"{system} {release}".format(system=platform.system(),
                                         release=platform.release())  # self.getLogin().get("device_name"),

device_uuid = uuid.getnode()  # MAC address #http://stackoverflow.com/questions/2461141/get-a-unique-computer-id-in-python-on-windows-and-linux
print device_uuid

class Settings(object): #http://stackoverflow.com/questions/9698614/super-raises-typeerror-must-be-type-not-classobj-for-new-style-class
    attrs = ["_app_name", "_settings", "_settings_name"]

    def __init__(self, app_name, settings_name="settings"):
        self._app_name = app_name
        self._settings_name = settings_name
        self._settings = None

    def __getattr__(self, field):
        # __getattr__ is last resort if _app_name was not found! Also there is no super __getattr__ # http://stackoverflow.com/questions/12047847/super-object-not-calling-getattr
        # no super __getattr__ needed since if the attr was already set in init, if you still want to override that feature, use __getattribute__ http://stackoverflow.com/questions/3278077/difference-between-getattr-vs-getattribute
        value = self._get_field(field)
        return value

    def __setattr__(self, field, value):
        if field in self.__class__.attrs:
            super(self.__class__, self).__setattr__(field, value)
            return
        self._set_field(field, value)

    def __delattr__(self, field):
        self._del_field(field)

    def _del_field(self, field):
        self._get_settings()
        del self._settings[field]  # raises key_error
        self._set_settings()

    def _get_settings(self):
        zlib = keyring.get_password(self._app_name, self._settings_name)
        if zlib:
            dump = zlib.decode("base64").decode("zlib")
        else:
            dump = "{}"
        self._settings = json.loads(dump)  # json.loads(dump or "null") # not used anymore since dump is True, but useful trick

    def _set_settings(self):
        dump = json.dumps(self._settings).encode("zlib").encode('base64')
        keyring.set_password(self._app_name, self._settings_name, dump)

    def _get_field(self, field):
        self._get_settings()
        value = self._settings[field]
        return value

    def _set_field(self, field, value):
        self._get_settings()
        self._settings.update({field:value})
        self._set_settings()

settings = Settings(app_name = "pastebeam")