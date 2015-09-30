#--coding: utf-8 --

import urlparse
import os, platform

SYSTEM = platform.system() #returns Windows, Darwin, Linux

import bson.json_util as json
from bson.binary import Binary

import hashlib, uuid, time, sys, cgi, tempfile

from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import HMAC,SHA512

import validators

from spooky import hash128

from collections import deque

#DEFAULT_DOMAIN = "192.168.0.191"
#DEFAULT_DOMAIN = "192.168.0.12"
DEFAULT_DOMAIN = "127.0.0.1"
DEFAULT_PORT = 8084

CONTAINER_DIR = os.path.join(tempfile.gettempdir(), u".pastebeam") #tempfile.mkdtemp() #TODO- use tempfile.mkdtemp() when extracting container, as it guarantees other programs will not be able to intercept extracted file, see tempfile docs for more info

def string_is_url(url):
	split_url = url.split()
	if len(url) < 2048 and len(split_url) == 1: #make sure text is under 2048 (for performance), and make sure the text is continuous like a url should be
		if bool(urlparse.urlparse(split_url[0]).scheme in ['http', 'https', 'ftp', 'ftps', 'bitcoin', 'magnet'] ): #http://stackoverflow.com/questions/25259134/how-can-i-check-whether-a-url-is-valid-using-urlparse
			return True
	return False

def getFolderSize(folder, max=None): #http://stackoverflow.com/questions/1392413/calculating-a-directory-size-using-python
	#recursively check folder size
	total_size = os.path.getsize(folder)
	for item in os.listdir(folder):
		itempath = os.path.join(folder, item)
		if os.path.isfile(itempath):
			total_size += os.path.getsize(itempath)
		elif os.path.isdir(itempath):
			total_size += getFolderSize(itempath)
		if max and total_size >= max:
			return float("inf") #1024*1024*1024*1024 #http://stackoverflow.com/questions/7781260/how-can-i-represent-an-infinite-number-in-python
	return total_size
	
	
#See: http://daringfireball.net/2010/07/improved_regex_for_matching_urls
import re, urllib

GRUBER_URLINTEXT_PAT = re.compile(ur'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))')

def PRINT(label, data):
	print "\n%s: %s"%(label.capitalize(), data)
	
def URL(scheme, addr, port, *_args, **_vars):
	url = "{scheme}://{addr}:{port}/".format(scheme=scheme, addr=addr, port=port)
	if _args:
		args = "/".join(_args)
		url+=args
	if _vars:
		url+="?"
		for key, value in _vars.items():
			url+="{key}={value}&".format(key=key, value=value)
		url=url[:-1]
	return url

def downloadContainerIfNotExist(data):
	if not data.get("container_name"):
		return
	container_name = data["container_name"]
	container_path = os.path.join(CONTAINER_DIR, container_name)
	print container_path
	
	if os.path.isfile(container_path):
		return container_path
	else:
		#TODO- show downloading file dialogue
		try:
			#urllib.urlretrieve(URL(arg="static/%s"%container_name,port=8084,scheme="http"), container_path)
			urllib.URLopener().retrieve(URL("http", DEFAULT_DOMAIN, DEFAULT_PORT, "static", container_name), container_path) #http://stackoverflow.com/questions/1308542/how-to-catch-404-error-in-urllib-urlretrieve
		except IOError:
			pass
		else:
			return container_path

