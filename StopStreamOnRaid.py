#
# Project     OBS Stop stream on raid
# @author     Durss
# @link       github.com/durss/OBS-StopStreamOnRaid
# @license    GPLv3 - Copyright (c) 2021 Durss
#
# Script created from this project:
# https://github.com/dmadison/OBS-ChatSpam
#

from threading import Timer
import obspython as obs
import socket
import time


class TwitchIRC:
	def __init__(self, chan="", passw="", host="irc.chat.twitch.tv", port=6667):
		self.channel = chan
		self.password = passw
		self.host = host
		self.port = port

		self.connected = False
		self.__last_message = 0.0  # Last connection timestamp
		self.timeout = 10.0  # Time before open connection is closed, in seconds

		self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.__sock.setblocking(0)

	def connect(self, suppress_warnings=True):
		print("Connecting...")
		connection_result = self.__connect()

		if connection_result is not True:
			self.connected = False
			if suppress_warnings:
				print("Connection Error:", connection_result)
				return False
			else:
				raise UserWarning(connection_result)

		self.connected = True
		return True

	def sendData(self, data):
		total_sent = 0
		data_size = len(data)
		while len(data):
			try:
				sent = self.__sock.send(data)
				total_sent += sent
				data = data[sent:]
			except e:
				if e.errno != errno.EAGAIN:
					raise e
				print('Blocking with', len(data), 'remaining')
				select.select([], [self.__sock], [])  # This blocks until

	def __connect(self):
		if self.connected:
			return True  # Already connected, nothing to see here

		self.__sock = socket.socket()
		self.__sock.settimeout(1)  # One second to connect

		try:
			self.__sock.connect((self.host, self.port))
		except socket.gaierror:
			return "Cannot find server"
		except (TimeoutError, socket.timeout):
			return "No response from server (connection timed out)"

		if self.password != "":
			self.sendData("PASS {}\r\n".format(self.password).encode("utf-8"))
		self.sendData("NICK {}\r\n".format(self.channel).encode("utf-8"))
		self.sendData("JOIN #{}\r\n".format(self.channel).encode("utf-8"))

		auth_response = self.read()
		if "Welcome, GLHF!" not in auth_response:
			return "Bad Authentication! Check your Oauth key"
		
		self.sendData("CAP REQ :twitch.tv/commands\r\n".encode("utf-8"))
		try:
			self.read()  # Wait for "JOIN" response
		except socket.timeout:
			return "Channel not found!"

		print("Connected to IRC", self.channel)
		return True

	def disconnect(self):
		if self.connected:
			self.__sock.shutdown(socket.SHUT_RDWR)
			self.__sock.close()
			self.connected = False

	def test_authentication(self):
		if self.connect(False):
			self.disconnect()
		print("Authentication successful!")

	def readAsync(self):
		try:
			self.__sock.setblocking(False)
			response = self.__sock.recv(1024).decode("utf-8")
			return response.rstrip()
		except BlockingIOError:
			pass

	def read(self):
		response = self.__read_socket()
		while self.__ping(response):
			response = self.__read_socket()
		return response.rstrip()

	def __read_socket(self):
		return self.__sock.recv(1024).decode("utf-8")

	def __ping(self, msg):
		if msg[:4] == "PING":
			self.__pong(msg[4:])
			return True
		return False

	def __pong(self, host):
		sendData(("PONG" + host).encode("utf-8"))

twitch = TwitchIRC()
connectTimer = None
# ------------------------------------------------------------

# OBS Script Functions

def test_authentication(prop, props):
	twitch.test_authentication()

def script_description():
	return "<b>Stop stream on Raid</b>" + \
			"<hr>" + \
			"Python script that closes OBS after a raid." + \
			"<br /><br />" + \
			"Generate an OAuth token from <a href='https://twitchapps.com/tmi/'>this page</a>."

def script_update(settings):
	global connectTimer
	twitch.channel = obs.obs_data_get_string(settings, "channel").lower()

	new_oauth = obs.obs_data_get_string(settings, "oauth").lower()
	if new_oauth != twitch.password:
		twitch.disconnect()  # Disconnect old oauth connection, if it exists
		twitch.password = new_oauth
	
	# Attempt to reconnect 1 second after last update
	if new_oauth and twitch.channel:
		if connectTimer:
			connectTimer.cancel()
			connectTimer = None
		connectTimer = Timer(1.0, twitch.connect)
		connectTimer.start()


def script_properties():
	props = obs.obs_properties_create()

	obs.obs_properties_add_text(props, "channel", "Channel", obs.OBS_TEXT_DEFAULT)
	obs.obs_properties_add_text(props, "oauth", "Oauth", obs.OBS_TEXT_PASSWORD)
	obs.obs_properties_add_button(props, "test_auth", "Test Authentication", test_authentication)

	return props


def script_load(settings):
	obs.timer_add(check_raid, 1000)  # Check for raid every second

def check_raid():
	if twitch.connected:
		res = ""
		try:
			res = twitch.readAsync()
		except socket.timeout:
			return
		if res:
			if res.find("HOSTTARGET") != -1:
				print("Raid detected!")
				obs.obs_frontend_streaming_stop()
				return

def script_unload():
	return True