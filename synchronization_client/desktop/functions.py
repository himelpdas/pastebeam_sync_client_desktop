import urlparse
import os

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
			return 1024*1024*1024*1024
	return total_size