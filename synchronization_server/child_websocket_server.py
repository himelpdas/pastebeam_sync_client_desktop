from gevent import monkey; monkey.patch_all() #declare BEFORE all imports

from base_non_blocking_server import *

from gevent.event import AsyncResult

import uuid

from bottle import Bottle, static_file
app = Bottle()

if os.name == "nt":
	UPLOAD_DIR="C:\\Users\\Himel\\Desktop\\test\\uploads"
else:
	UPLOAD_DIR="/home/das/Projects/junk/"
	
@app.route('/echo')
def test_async_websocket():
	wsock = request.environ.get('wsgi.websocket')
	if not wsock:
		abort(400, 'Expected WebSocket request.')

	while True:
		try:	
			message = wsock.receive()
			#sleep(8)
			wsock.send(message)
		except WebSocketError:
			break
	
@app.route('/ws')
def handle_websocket():
	
	gevent.sleep(1)
	
	def _incoming(wsock, timeout): #these seem to run in another namespace, you must pass them global or inner variables

		try:
			client_previous_clip = get_latest_row_and_clips()['latest_row'] or {} #SHOULD CHECK SERVER TO AVOID RACE CONDITIONS? #too much bandwidth if receiving row itself, only text and hash are fine (data)
			
			for second in range(timeout): #Even though greenlets don't use much memory, if the user disconnects, this server greenlet will run forever, and this "little memory" will become a big problem

				received = wsock.receive()
				
				if not received:
					raise WebSocketError
					
				delivered = json.loads(received)
				
				if delivered['message'] == "Alive?":
			
					send_im_still_alive.set(1)
					
				if delivered["message"] == "Salt?":
				
					send_usr_crypt_salt.set(checked_login["found"]["salt"])
					
				if delivered['message'] == "Upload?":
				
					container_name =  delivered['data']
					
					file_path = os.path.join(UPLOAD_DIR,container_name)
					file_exists = os.path.isfile(file_path)
					send_upload_command.set({container_name:file_exists})
					print "\nFILE EXISTS:%s\n"%file_exists
			
				elif delivered['message'] == "Update?":
					
					client_latest_clip = delivered['data']
														
					if client_latest_clip.get('clip_hash_secure') != client_previous_clip.get('clip_hash_secure'): #else just wait
						
						client_latest_clip['timestamp_server'] = time.time()
						new_clip_id = clips.insert_one(client_latest_clip) 
						
						print "INSERTED:%s "% new_clip_id

						client_previous_clip = client_latest_clip #reset prev
					
					else:
						print "hashes match, request rejected"
						print "OLD: \n%s - %s\nNEW:%s - %s"%(client_previous_clip.get('clip_hash_secure'), client_previous_clip.get("clip_file_name"), client_latest_clip.get('clip_hash_secure'), client_latest_clip.get('clip_file_name') )
				
				print "incoming wait..."
				sleep(0.1)
		except ZeroDivisionError:
			#print "incoming error...%s"%str(sys.exc_info()[0]) #http://goo.gl/cmtlsL
			pass
		finally:
			wsock.close() #OR IT WILL LEAVE THE CLIENT HANGING!

	def _outgoing(wsock, timeout):
		try:
			server_previous_row = {'_id':None}
			for second in range(timeout):
				if send_im_still_alive.get():
					wsock.send(json.dumps(dict(
						message = "Alive!"
					))) #send blank list of clips to tell client's incoming server is still alive.
					send_im_still_alive.set(0)
				if send_usr_crypt_salt.get():
					wsock.send(json.dumps(dict(
						message = "Salt!",
						data = send_usr_crypt_salt.get()
					)))
					send_usr_crypt_salt.set(None)
				elif send_upload_command.get():
					wsock.send(json.dumps(dict(
						message = "Upload!",
						data = send_upload_command.get(),
					)))
					send_upload_command.set({})
				else:
					server_latest_row_and_clips = get_latest_row_and_clips()
					server_latest_row = server_latest_row_and_clips['latest_row']
					server_latest_clips = server_latest_row_and_clips['latest_clips']
					if server_latest_row:
						#print server_latest_row
						if server_latest_row['_id'] != server_previous_row['_id']:
							#print "if server_latest_row['_id'] != server_previous_row['_id']")
							wsock.send(json.dumps(dict(
								message = "Update!",
								data = server_latest_clips,
							)))
							#print server_latest_row)
							
							server_previous_row = server_latest_row #reset prev
				
				#print "outgoing wait...")
				sleep(0.1)
		except ZeroDivisionError:
			#print "outgoing error...%s"%str(sys.exc_info()[0]) #http://goo.gl/cmtlsL
			pass
		finally:
			wsock.close()

	try:		
	
		wsock = request.environ.get('wsgi.websocket')
				
		if not wsock:
			abort(400, 'Expected WebSocket request.')

		checked_login = login(request.query.email, request.query.password)

		if not checked_login['success']:
			
			wsock.send(json.dumps(dict(
				message = "Error!",
				data = checked_login["reason"],
			)))
			
		else:
			timeout=40000
					
			args = [wsock, timeout] #Only objects in the main thread are visible to greenlets, all other cases, pass the objects as arguments to greenlet.
					
			send_im_still_alive, send_upload_command, send_usr_crypt_salt = AsyncResult(), AsyncResult(), AsyncResult()
			send_im_still_alive.set(0)
			send_usr_crypt_salt.set(None)
			send_upload_command.set({})	
			#send_update_command.set(None)
					
			greenlets = [
				gevent.spawn(_incoming, *args),
				gevent.spawn(_outgoing, *args),
			]
			gevent.joinall(greenlets)

	except WebSocketError:
		abort(500, 'Websocket failure.')
	finally:
		wsock.close()
		
@app.get('/file_exists/<filename>')
def file_exists(filename):
	response.content_type =  "application/json; charset=UTF8"

	file_path = os.path.join(UPLOAD_DIR,filename)
	file_exists = os.path.isfile(file_path)
	print "\nFILE EXISTS:%s\n"%file_exists
	
	return json.dumps({"result":file_exists})
		
@app.post('/upload')
def handle_upload():
	#print "HANDLE HANDLE HANDLE"
	result = "OK"
	save_path = UPLOAD_DIR

	upload    = request.files.get('upload')
	
	name, ext = os.path.splitext(upload.filename)
	"""
	if ext not in (".txt",'.bmp','.png','.jpg','.jpeg', '.py'):
		result = 'File extension not allowed.'
	else:
		upload.save(save_path, overwrite=False) # appends upload.filename automatically
	"""
	try:
		upload.save(save_path, overwrite=False) # appends upload.filename automatically
	except IOError:
		pass
		
	response.content_type =  "application/json; charset=UTF8"
	return json.dumps({"upload_result":result})

@app.get('/static/<filename>')
def handle_download(filename):
	return static_file(filename, root=UPLOAD_DIR)
	
@app.get('/auth/<email>/<password>')
def register(email,password):
	response.content_type =  "application/json; charset=UTF8"

	found = accounts.find_one({'email': email})

	if not validators.email(email):
		return json.dumps({"success": False, "reason":"Invalid email!"})
	if found:
		return json.dumps({"success": False, "reason":"Email already exists!"})
	if len(password) < 8:
		return json.dumps({"success": False, "reason":"Password too short!"})

	random_bytes = Crypto.Random.get_random_bytes(16).encode("base64")
	key_derivation = PBKDF2(password, random_bytes).encode("base64")
	new_account_id = accounts.insert_one({"email":email, "key_derivation":key_derivation, "salt":random_bytes})
	return {"success":True, "Reason":"Account %s successfully created!"%new_account_id}
	
if __name__ == "__main__":
	#geventwebsocket implementation
	from gevent.pywsgi import WSGIServer
	from geventwebsocket import WebSocketError
	from geventwebsocket.handler import WebSocketHandler
	server = WSGIServer(("0.0.0.0", 8084), app,
						handler_class=WebSocketHandler)
	server.serve_forever()

"""
##ws4py implementation (doesn't work)
#from gevent import monkey; monkey.patch_all()
from ws4py.server.geventserver import WSGIServer
from ws4py.server.geventserver import WebSocketWSGIHandler
from ws4py.exc import WebSocketException

server = WSGIServer(("0.0.0.0", 8084), app,
					handler_class=WebSocketHandler )
server.serve_forever()
"""
