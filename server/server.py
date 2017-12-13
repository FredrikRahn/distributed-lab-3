
# coding=utf-8
#------------------------------------------------------------------------------------------------------
# TDA596 Labs - Server Skeleton
# server/server.py
# Input: Node_ID total_number_of_ID
# Student Group: 99
# Student names: Fredrik Rahn & Alexander Branzell
#------------------------------------------------------------------------------------------------------
# We import various libraries
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler # Socket specifically designed to handle HTTP requests
import sys # Retrieve arguments
import os 	#OS
import time #time
import json #debuggin
from operator import itemgetter # import itemgetter for sorting
from urlparse import parse_qs # Parse POST data
from httplib import HTTPConnection # Create a HTTP connection, as a client (for POST requests to the other vessels)
from urllib import urlencode # Encode POST content into the HTTP header
from codecs import open # Open a file
from threading import  Thread, Timer # Thread Management
#------------------------------------------------------------------------------------------------------
#Get correct folder path
file_folder = os.path.dirname(os.path.realpath(__file__)) + '/'
# Global variables for HTML templates
board_frontpage_header_template = open(file_folder + 'board_frontpage_header_template.html', 'r').read()
boardcontents_template = open(file_folder + 'boardcontents_template.html', 'r').read()
entry_template = open(file_folder + 'entry_template.html', 'r').read()
board_frontpage_footer_template = open(file_folder + 'board_frontpage_footer_template.html', 'r').read()
#------------------------------------------------------------------------------------------------------
# Static variables definitions
PORT_NUMBER = 80
#------------------------------------------------------------------------------------------------------
class BlackboardServer(HTTPServer):
#------------------------------------------------------------------------------------------------------
	def __init__(self, server_address, handler, node_id, vessel_list):
		'''
		Init of Blackboard HTTP server
		@args:	server_address:String, Address to Server
				handler:BaseHTTPRequestHandler, Server handler
				node_id:Number, The ID of the node
				vessel_list:[String], list of vessels
		@return:
		'''
		# We call the super init
		HTTPServer.__init__(self,server_address, handler)
		# we create the dictionary of values
		self.store = {}
		# We keep a variable of the next id to insert
		self.current_key = -1
		# our own ID (IP is 10.1.0.ID)
		self.vessel_id = vessel_id
		# The list of other vessels
		self.vessels = vessel_list
		# Event queue
		self.event_log = {}
		# Time
		self.start_time = 0

#------------------------------------------------------------------------------------------------------
	# We add a value received to the store
	def add_value_to_store(self, value):
		'''
		Adds a new value to store
		@args: Value:String, Value to be added to store
		@return: [Key:String, Value:String]
		'''
		# We add the value to the store
		self.current_key += 1
		key = self.current_key
		seq_id = round(time.time(),2)
		sender_id = self.vessel_id
		if key not in self.store:
			self.store[key]=[seq_id, sender_id, value]
			return [seq_id, sender_id, key, value]
		else:
			raise KeyError('Can not add key (Already Exists)')
#------------------------------------------------------------------------------------------------------
	# We add a value received to the store
	def add_value_to_store_from_propagate(self, seq_id, sender_id, key, value):
		'''
		Adds a new value to store
		@args: Value:String, Value to be added to store
		@return: [Key:String, Value:String]
		'''
		# We add the value to the store
		seq_id = float(seq_id)
		self.current_key = key
		if key not in self.store:
			self.store[key]=[seq_id, sender_id, value]
			return [seq_id, sender_id, key, value]
		else:
			raise KeyError('Can not add key (Already Exists)')
                #a new key has been added, do we have actions stored for it?
                action_queue = self.event_log.get(key)
                if action_queue:
                        #Yes, we do have actions in store for it.
                        for i in range(len(action_queue)-1):
                                action = action_queue[i]
                                if(action[0] == 'modify' and self.store.get(key)[0] < action[1]):
                                        self.modify_value_in_store(seq_id = action[1], sender_id = action[2], value=action[3])
                                elif(action[0] == 'modify' and self.store.get(key)[0] == action[1] and self.store.get(key)[1] < action[2]):
                                        self.modify_value_in_store(seq_id = action[1], sender_id = action[2], value=action[3])
                                elif(action[0] == 'delete'):
                                     self.delete_value_in_store(key, action[1])
                                     #Delete has been done, delete all actions stored and break loop.
                                     del event_log[key]
                                     break

#------------------------------------------------------------------------------------------------------
	# We modify a value received in the store
	def modify_value_in_store(self, seq_id, sender_id, key, value):
		'''
		Modifies value in store
		@args:	Key:Number, 	Key to be modified
				Value:String, 	Value to be added to key
		@return: [Key:Number, Value:String]
		'''
		seq_id = float(seq_id)
		if key in self.store:
			self.store[key] = [seq_id, sender_id, value]
			return [seq_id, sender_id, key, value]
		else:
			raise KeyError('Key does not exist in store')
#------------------------------------------------------------------------------------------------------
	def delete_value_in_store(self, key, seq_id):
		'''
		Deletes value in store
		@args:	Key:Number, Key to be deleted
		@return: [Key:String]
		'''
		seq_id = float(seq_id)
		if key in self.store:
			entry = self.store.get(key)
			del self.store[key]
		return [entry[0], entry[1], key, entry[2]]
#------------------------------------------------------------------------------------------------------

# Contact a specific vessel with a set of variables to transmit to it
	def contact_vessel(self, vessel_ip, path, action, seq_id, sender_id, key, value):
		'''
		Handles contact with specific vessel
		@args:	Vessel_ip:String, 	IP to the vessel
				Path:String, 		The path where the request will be sent
				Action:Any, 		Action to be performed
				Key:Number, 		Key for store
				Value:String, 		Value for store
		@return:Entire page:html
		'''
		# the Boolean variable we will return
		success = False
		# The variables must be encoded in the URL format, through urllib.urlencode
		post_content = urlencode({'action': action, 'seq_id': seq_id, 'sender_id': sender_id, 'key': key, 'value': value})
		# the HTTP header must contain the type of data we are transmitting, here URL encoded
		headers = {"Content-type": "application/x-www-form-urlencoded"}
		# We should try to catch errors when contacting the vessel
		try:
			# We contact vessel:PORT_NUMBER since we all use the same port
			# We can set a timeout, after which the connection fails if nothing happened
			connection = HTTPConnection("%s:%d" % (vessel_ip, PORT_NUMBER), timeout = 30)
			# We only use POST to send data (PUT and DELETE not supported)
			action_type = "POST"
			# We send the HTTP request
			connection.request(action_type, path, post_content, headers)
			# We retrieve the response
			response = connection.getresponse()
			# We want to check the status, the body should be empty
			status = response.status
			# If we receive a HTTP 200 - OK
			if status == 200:
				success = True
		# We catch every possible exceptions
		except Exception as e:
			print "Error while contacting %s" % vessel_ip
			# printing the error given by Python
			print(e)

		# we return if we succeeded or not
		return success
#------------------------------------------------------------------------------------------------------
	# We send a received value to all the other vessels of the system
	def propagate_value_to_vessels(self, path, action, seq_id, sender_id, key, value):
		'''
		Handles propagation of requests to vessels
		@args:	Path:String,	The path where the request will be sent
				Action:String, 	The action that should be performed by the other vessels
				Key:Number, 	Key that should be used in action
				Value:String, 	Value corresponding to key
		@return:
		'''
		for vessel in self.vessels:
			# We should not send it to our own IP, or we would create an infinite loop of updates
			if vessel != ("10.1.0.%s" % self.vessel_id):
				# A good practice would be to try again if the request failed
				# Here, we do it only once
				self.contact_vessel(vessel, path, action, seq_id, sender_id, key, value)
#------------------------------------------------------------------------------------------------------
# This class implements the logic when a server receives a GET or POST
# It can access to the server data through self.server.*
# i.e. the store is accessible through self.server.store
# Attributes of the server are SHARED accross all request hqndling/ threads!
class BlackboardRequestHandler(BaseHTTPRequestHandler):
#------------------------------------------------------------------------------------------------------
	# We fill the HTTP headers
	def set_HTTP_headers(self, status_code = 200):
		'''
		Sets HTTP headers and status code of the response
		@args: Status_code, status code to put in header
		'''
		 # We set the response status code (200 if OK, something else otherwise)
		self.send_response(status_code)
		# We set the content type to HTML
		self.send_header("Content-type","text/html")
		# No more important headers, we can close them
		self.end_headers()
#------------------------------------------------------------------------------------------------------
	# a POST request must be parsed through urlparse.parse_QS, since the content is URL encoded
	def parse_POST_request(self):
		'''
		Parses POST requests
		@args:
		@return: post_data:Dict returns dictionary of URL-encoded data
		'''
		post_data = ""
		# We need to parse the response, so we must know the length of the content
		length = int(self.headers['Content-Length'])
		# we can now parse the content using parse_qs
		post_data = parse_qs(self.rfile.read(length), keep_blank_values=1)
		# we return the data
		return post_data
#------------------------------------------------------------------------------------------------------
# Request handling - GET
#------------------------------------------------------------------------------------------------------
	def do_GET(self):
		'''
		Handles incoming GET requests and routes them accordingly
		'''

		with open(file_folder + "logs/" + "store_vessel_%d" % self.server.vessel_id, "w+") as file:
			for item in self.server.store.values():
				data = item[0], item[1]
				file.write(json.dumps(data)+"\n")

		print("Receiving a GET on path %s" % self.path)
		path = self.path[1::].split('/')
		if path[0] == 'board':
			self.do_GET_board()
		elif path[0] == 'entry' and len(path) > 1:
			self.do_GET_entry(path[1])
		else:
			self.do_GET_Index()		#Unknown path, route user to index
#------------------------------------------------------------------------------------------------------
	def do_GET_Index(self):
		'''
		Fetches the Index page and all contents to be displayed
		@return: Entire page:html
		'''
		# We set the response status code to 200 (OK)
		self.set_HTTP_headers(200)

		fetch_index_header = board_frontpage_header_template
		fetch_index_contents = self.board_helper()
		fetch_index_footer = board_frontpage_footer_template

		html_response = fetch_index_header + fetch_index_contents + fetch_index_footer

		self.wfile.write(html_response)
#------------------------------------------------------------------------------------------------------
	def board_helper(self):
		'''
		Helper func for fetching board contents
		@return: List of boardcontents
		'''
		fetch_index_entries = ""
		for entryId, entryValue in self.server.store.items():
			fetch_index_entries += entry_template %("entries/" + str(entryId), int(entryId), str(entryValue[0]), str(entryValue[2]))
		boardcontents = boardcontents_template % ("Title", fetch_index_entries)
		return boardcontents
#------------------------------------------------------------------------------------------------------
	def do_GET_board(self):
		'''
		Fetches the board and its contents
		'''
		self.set_HTTP_headers(200)
		html_response = self.board_helper()
		self.wfile.write(html_response)
#------------------------------------------------------------------------------------------------------
	def do_GET_entry(self, entryID):
		'''
		Retrieve an entry from store and inserts it into the entry_template
		@args: entryID:String, ID of entry to be retrieved
		@return: Entry:html
		'''
		#Find the specific value for the entry, if entry does not exist set value to None
		entryValue = self.server.store[entryId] if entryId in self.server.store else None
		#Return found entry if it exists, or return empty string if no such entry was found
		return entry_template %("entries/" + entryId, entryId, entryValue) if entryValue != None else ""
#------------------------------------------------------------------------------------------------------
# Request handling - POST
#------------------------------------------------------------------------------------------------------
	def do_POST(self):
		'''
		Handles incoming POST requests and routes them accordingly
		'''
		print("Receiving a POST on %s" % self.path)
		# Save time for benchmarking
		with open(file_folder + "logs/" + "last_request_vessel_%d" % self.server.vessel_id, "w+") as file:
			if(self.server.start_time == 0):
				self.server.start_time = time.time()
			last_post = time.time()

			file.write(json.dumps(self.server.start_time-last_post)+"\n")

		path = self.path[1::].split('/')
		if path[0] == 'board' and len(path) < 2:
			self.do_POST_board()
		elif path[0] == 'entries' and len(path) > 1:
			self.do_POST_entries(path[1])
		elif path[0] == 'propagate':
			self.do_POST_propagate()
#------------------------------------------------------------------------------------------------------
	def do_POST_board(self):
		'''
		Add entries to board
		'''
		post_data = self.parse_POST_request()
		if 'entry' in post_data:
			value = post_data['entry'][0]

			entry = self.do_POST_add_entry(value)
			self.propagate_action(action='add', seq_id=entry[0], sender_id=entry[1], key=entry[2], value=entry[3])
		else:
			self.send_error(400, 'Error adding entry to board')
#------------------------------------------------------------------------------------------------------
	def do_POST_entries(self, key):
		'''
		Handles deleting and modifying entries to the board
		@args: entryID:String, ID of entry to be modified/deleted
		'''
		post_data = self.parse_POST_request()
		key=int(key)
		print(post_data)
		if 'delete' in post_data:
			delete = post_data['delete'][0]
			if delete == '1':
				# local delete
				entry = self.do_POST_delete_entry(seq_id=time.time(), key=key)
				self.propagate_action(action='delete', seq_id=entry[0], sender_id=entry[1],  key=entry[2], value=entry[3])
			else:
				old_entry = self.server.store.get(key)
				entry = self.do_POST_modify_entry(key, post_data['entry'][0])
				self.propagate_action(action='modify', seq_id=entry[0], sender_id=entry[1],  key=entry[2], value=entry[3])
		else:
			self.send_error(400, 'Delete flag missing from request')
#------------------------------------------------------------------------------------------------------
	def do_POST_propagate(self):
		'''
		Handles propagation of actions by
		routing them to the correct functions
		'''
		post_data = self.parse_POST_request()
		if 'action' in post_data:
			action = post_data['action'][0]
			seq_id = post_data['seq_id'][0]
			sender_id = post_data['sender_id'][0]
			value = post_data['value'][0]
			key = post_data['key'][0]

			if action == 'add':
                                #handle collisions, then add
				entry = self.handle_collisions(seq_id=seq_id, sender_id=sender_id, key=key, value=value)
				entry = self.do_POST_add_entry_from_propagate(seq_id=entry[0], sender_id=entry[1], key=entry[2], value=entry[3])
			elif action == 'modify':
				entry = self.do_POST_modify_entry_from_propagate(seq_id=seq_id, sender_id=sender_id, key=key, value=value)
			elif action == 'delete':
				entry = self.do_POST_delete_entry_from_propagate(seq_id=seq_id, sender_id=sender_id, key=key, value=value)
			else:
				self.send_error(400, 'Invalid action')
#------------------------------------------------------------------------------------------------------
	def do_POST_add_entry(self, value):
		'''
		Adds a new entry to store
		@args: value:Value, Value to be added in store
		@return: entry:List, [key, value]
		'''
		entry = self.server.add_value_to_store(value=value)
		if entry:
			self.send_response(200)
			return entry
		else:
			self.send_error(400, "Value was not added.")
#------------------------------------------------------------------------------------------------------
	def do_POST_add_entry_from_propagate(self, seq_id, sender_id, key, value):
		'''
		Adds a new entry to store
		@args: value:Value, Value to be added in store
		@return: entry:List, [key, value]
		'''
		entry = self.server.add_value_to_store_from_propagate(seq_id=seq_id, sender_id=sender_id, key=key, value=value)
		if entry:
			self.send_response(200)
			return entry
		else:
			self.send_error(400, "Value was not added.")
#------------------------------------------------------------------------------------------------------
	def do_POST_modify_entry_from_propagate(self, seq_id, sender_id, key, value):
		'''
		Modifies a specific entry in store
		@args: entryID:String, ID of entry to be modified
		@args: value:String, new value to be assigned to entryID
		@return: entry:List, [key, value]
		'''
		#Check if the modify is a a later change
		key = int(key)
		seq_id = float(seq_id)
		sender_id = int(sender_id)
		entry = self.server.store.get(key)
		print('trying to modify :', entry)
		if entry and seq_id > entry[0]:

			# If entry exists and action occured after entry in store, modify entry
			entry = self.server.modify_value_in_store(seq_id=seq_id, sender_id=sender_id, key=key, value=value)

			self.send_response(200)
			return entry

		elif entry and seq_id == entry[0]:
			# If seq_ids are equal the action with higher sender_id gets priority
			if sender_id > entry[1]:
				# Only modify if sender_id is larger than store sender_id
				entry = self.server.modify_value_in_store(seq_id=seq_id, sender_id=sender_id, key=key, value=value)

				self.send_response(200)
				return entry
		else:
                        #key does not exist... yet! Append action to action queue.
                        action_queue = self.server.event_log.get(key)
                        if action_queue:
                                #do we need double list in order to not append?
                                action_queue = action_queue + [['modify', seq_id, sender_id, value]]
                        else:
                                action_queue = [['modify', seq_id, sender_id, value]]
                        action_queue = sorted(action_queue, key=itemgetter(2))
                        self.server.event_log[key] = action_queue
			self.send_response(200)
#------------------------------------------------------------------------------------------------------
	def do_POST_modify_entry(self, key, value):
		# This function handles local modify, so we append seq_id and
		# sender_id before function call
		seq_id = time.time()
		sender_id = self.server.vessel_id

		entry = self.server.modify_value_in_store(seq_id=seq_id, sender_id=sender_id, key=key, value=value)
		if entry:
			self.send_response(200)
			return entry
		else:
			 self.send_error(400, 'Entry not modified')
#------------------------------------------------------------------------------------------------------
	def do_POST_delete_entry_from_propagate(self, seq_id, sender_id, key, value):
		'''
		Deletes an entry in store
		@args: entryID:String
		@return: entry:List, [key]
		'''
		seq_id = float(seq_id)
		sender_id = int(sender_id)
		key = int(key)
		entry = self.server.store.get(key)
		print('entry in store: ', entry, 'entry from sender: ', [seq_id, sender_id, key, value])
		if entry and seq_id == entry[0] and sender_id == entry[1] and value == entry[2]:
			entry = self.server.delete_value_in_store(seq_id=seq_id, key=key)
			self.send_response(200)
			return entry
		else:
                        #key does not exist... yet! Append action to action queue.
                        action_queue = self.server.event_log.get(key)
                        if action_queue:
                                #do we need double list in order to not append?
                                action_queue = action_queue + [['delete', seq_id, sender_id, value]]
                        else:
                                action_queue = [['delete', seq_id, sender_id, value]]
                        #sort the queue on action id
                        action_queue = sorted(action_queue, key=itemgetter(1))
                        self.server.event_log[key] = action_queue
			self.send_response(200)
#------------------------------------------------------------------------------------------------------
	def do_POST_delete_entry(self, seq_id, key):
		# local delete
		entry = self.server.store.get(key)
		if entry:
			entry = self.server.delete_value_in_store(seq_id=seq_id,key=key)
			self.send_response(200)
			return entry
		else:
			 self.send_error(400, 'Entry not deleted')
#------------------------------------------------------------------------------------------------------
	def handle_collisions(self, seq_id, sender_id, key, value):
		#check collision
		seq_id = float(seq_id)
		sender_id = int(sender_id)
		key = int(key)
		entry = self.server.store.get(key)
		if entry:
			# key already exists in store
			if entry[0] > seq_id:
				# post in store is older, replace with new values and dorecursive call with the older values
				self.server.modify_value_in_store(seq_id=seq_id, sender_id=sender_id, key=key, value=value)
				return self.handle_collisions(seq_id=entry[0], sender_id=entry[1], key=key+1, value=entry[2])
			elif entry[0] == seq_id and entry[1] < sender_id:
				# Seq_ids equal and newer entry has priority, fix tiebreaker
				# only modify entry in store if store sender id is less than new sender
				self.server.modify_value_in_store(seq_id=seq_id, sender_id=sender_id, key=key, value=value)
				return self.handle_collisions(seq_id=entry[0], sender_id=entry[1], key=key+1, value=entry[2])
			else:
				return self.handle_collisions(seq_id=seq_id, sender_id=sender_id, key=key+1, value=value)
		else:
			# Key doesnt exist in store, return
			print('No collision - RETURNING: ', 'seq_id: %d' %seq_id, 'sender_id: %d' % sender_id, 'value: %s' % value)
			return seq_id, sender_id, key, value

#------------------------------------------------------------------------------------------------------
	def propagate_action(self, action, seq_id, sender_id, key='', value=''):
		'''
		Spawns a thread and propagates an action to other vessels
		@args: action:String
		@args: key:String
		@args: value:String
		'''
		propagate_path = '/propagate'
		print('path, action, seq_id, key, value, sender_id', propagate_path, action, seq_id, sender_id, key, value)
		thread = Thread(target=self.server.propagate_value_to_vessels, args=(propagate_path, action, seq_id, sender_id, key, value))
		print('tried to propagate')

		# We kill the process if we kill the serverx
		thread.daemon = True
		# We start the thread
		thread.start()
#------------------------------------------------------------------------------------------------------
# Execute the code
if __name__ == '__main__':

	## read the templates from the corresponding html files
	# .....

	vessel_list = []
	vessel_id = 0
	# Checking the arguments
	if len(sys.argv) != 3: # 2 args, the script and the vessel name
		print("Arguments: vessel_ID number_of_vessels")
	else:
		# We need to know the vessel IP
		vessel_id = int(sys.argv[1])
		# We need to write the other vessels IP, based on the knowledge of their number
		for i in range(1, int(sys.argv[2])+1):
			vessel_list.append("10.1.0.%d" % i) # We can add ourselves, we have a test in the propagation

	# We launch a server
	server = BlackboardServer(('', PORT_NUMBER), BlackboardRequestHandler, vessel_id, vessel_list)
	print("Starting the server on port %d" % PORT_NUMBER)

	try:
		server.serve_forever()
	except KeyboardInterrupt:
		server.server_close()
		print("Stopping Server")
#------------------------------------------------------------------------------------------------------
