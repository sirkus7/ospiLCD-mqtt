#!/usr/bin/env python

"""
OpenSprinkler pi I2C LCD, remote MQTT enabled monitor
Based on Code by Stanley https://github.com/stanoba/
Enhanced by Sirkus7 https://github.com/sirkus7
Version: 0.1

"""

import signal
import sys
import time
from threading import Timer
import json
import locale
from collections import namedtuple
from time import *
from RPLCD import i2c
from subprocess import check_output
import netifaces
import paho.mqtt.client as mqtt
from urllib2 import urlopen # For Python3: from urllib.request import urlopen	

################ Parameters ####################
mqttAddress = "192.168.10.10"  # SET TO IP Address (or hostname) of MQTT broker (server)
mqttPort   = "1883" # Port of MQTT broker
osAddress = "127.0.0.1"  # SET TO OpenSprinkler address
osPort = 8080  # OpenSprinkler port (default 8080)
md5hash = "a6d82bced638de3def1e9bbb4983225c"  # OpenSprinkler password MD5 hash (default opendoor)
LCD_i2c_expander = 'PCF8574'  # PCF8574 (default, ebay), MCP23008 (used in Adafruit I2C LCD backpack) or MCP23017
LCD_i2c_address = 0x27  # LCD I2C address (default 0x27)
LCD_cols = 20  # LCD columns (16 or 20)
LCD_rows = 4   # LCD rows (2 or 4)
date_locale = 'en_US.UTF-8'  # Set to your Raspberry pi locale eg. 'en_GB.UTF-8' or 'it_IT.UTF-8'
net_iface = 'wlan0' # Set to network interface used for communication (eg. wlan0, eth0)
backlight_timeout = 60.0 # Float, seconds to keep display lit after showing data before dimming

"""
# Use this python code to generate md5hash of your OpenSprinkler password
import md5
md5hash=md5.new('opendoor').hexdigest()
print(md5hash)
"""

################################################
# Function defs

def signal_handler(sig, frame):
	global lcd
	global dim_timer
	dim_timer.cancel()
	lcd.backlight_enabled = False
	lcd.clear()
	print('Exiting.')
	sys.exit(0)

def mqtt_connect(client, userdata, flags, rc):
	#print("[Connected with result code {0}]".format(str(rc))) # For debugging MQTT connect message
	client.subscribe("opensprinkler/#")  # Subscribe to the topic, receive any messages published on it
	lcd.backlight_enabled = True
	lcd.cursor_pos = (0, 0)
	lcd.write_string("MQTT Connected\r\nReqesting info")

def mqtt_message(client, userdata, msg):  # The callback for when a PUBLISH message is received from the server.
	#print('Msg:' + msg.topic + ": " + str(msg.payload))  # Debug MQTT messages recieved.
	update_display()

def get_data(url):
	data = urlopen(url).read()
	data = data.replace("\"pass\":", "\"password\":") # Replace protected keyword "pass" with acceptable term "password"
	variables = json.loads(data, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
	return variables

def dim_backlight(): # Callback for dim_timer
	global lcd
	lcd.backlight_enabled = False
	print("[Backlight dimmed.]")

def update_display():
	global lcd
	global dim_timer

	# Parse JSON into an object with attributes corresponding to dict keys.
	ja = get_data(api_url)

	# get all station status
	mc = ''
	i = 1
	for x in range(0, 8):
		if ja.status.sn[x] == 0:
			mc = mc+"_"
		else:
			if i == ja.options.mas:  # MATER 1
				mc = mc+"M"
			elif i == ja.options.mas2:  # MASTER 2
				mc = mc+"N"
			else:
				mc = mc+str(i)
		i += 1

	mc2 = ''
	a = 9
	if ja.status.nstations > 8:
		for b in range(8, 16):
			if ja.status.sn[b] == 0:
				mc2 = mc2+"_"
			else:
				if a == ja.options.mas:  # MATER 1
					mc2 = mc2+"M"
				elif a == ja.options.mas2:  # MASTER 2
					mc2 = mc2+"N"
				else:
					mc2 = mc2+str(a)
			a += 1


	# get system status
	if ja.options.den == 0:
		mc = 'Disabled!'
	else:
		mc = mc+' '

	# get remote extension mode status
	if ja.options.re == 1:
		mc = mc+'\x05'
	else:
		mc = mc+' '

	# get sensor (0=none, 1=rain, 2=flow, 3=soil, 240=program switch)
	if ja.options.sn1t == 1:
		if ja.settings.rd == 1 or ja.settings.rs == 1:
			mc = mc+'\x03'
		else:
			mc = mc+' '
	elif ja.options.sn1t == 2:
		mc = mc+'\x06'
	elif ja.options.sn1t == 240:
		mc = mc+'\x07'
	else:
		mc = mc+' ' # Note, currently no icon for 3=soil. (todo)

	# get uSD status
	if ja.settings.wto:
		mc = mc+'\x02'
	else:
		mc = mc+''

	# check local network status
	net_ip = netifaces.ifaddresses(net_iface)[2][0]['addr']
	if len(net_ip) > 7:
		mc = mc+'\x00'
	else:
		mc = mc+'\x01'

	# Count remaining watering time
	totaltime = 0
	for station in ja.settings.ps:
		totaltime = totaltime+station[1]
	r_m, r_s = divmod(totaltime, 60)
	r_h, r_m = divmod(r_m, 60)

	

	# Define LCD lines 1 & 2
	locale.setlocale(locale.LC_ALL, date_locale)
	line1 = strftime("%H:%M %a %m-%d", gmtime(ja.settings.devt))  # device time
	line2 = "MC:"+mc  # station status

	# 3rd LCD line
	if ja.status.nstations > 8:
		line3 = "E1:"+mc2+" "+str(ja.options.wl)+"%"
	else:
		line3 = "Water level:"+str(ja.options.wl)+"%"

	# 4th LCD line
	if totaltime > 0:
		line4 = "Rt:%d:%02d:%02d h:m:s" % (r_h, r_m, r_s)  # Remaining watering time
	else:
		if len(net_ip) > 7:
			line4 = ""+net_ip  # internal IP
		else:
			line4 = "No Network!"

	print(line1)
	print(line2)
	if LCD_rows == 4:
		print (line3)
		print (line4)

	# Enable backlight to display new message.
	lcd.backlight_enabled = True

	# Write new information
	lcd.cursor_pos = (0, 0)
	lcd.write_string(line1)
	lcd.cursor_pos = (1, 0)
	lcd.write_string(line2)
	if LCD_rows == 4:
		lcd.cursor_pos = (2, 0)
		lcd.write_string(line3)
		lcd.cursor_pos = (3, 0)
		lcd.write_string(line4)

	# If "lit" parameter exists and enabled, stay lit, otherwise, dim after backlight_timeout seconds
	if  not ("lit" in ja.options and ja.options.lit > 1):
		dim_timer.cancel()
		dim_timer = Timer(backlight_timeout, dim_backlight)
		dim_timer.start() 

##################################################################################3
# Globals
backlight = True
dim_timer = ""
api_url   = ("http://"+osAddress+":"+str(osPort)+"/ja?pw="+md5hash)
dim_timer = Timer(backlight_timeout, dim_backlight)

signal.signal(signal.SIGINT, signal_handler)

# === Setup the Display ===
lcd = i2c.CharLCD(i2c_expander=LCD_i2c_expander, address=LCD_i2c_address, port=1, cols=LCD_cols, rows=LCD_rows,
						dotsize=8, charmap='A02', auto_linebreaks=True, backlight_enabled=True)

# Define Custom LCD characters
i_wific = (0b00000, 0b00000, 0b00000, 0b00001, 0b00001, 0b00101, 0b00101, 0b10101)  # Wifi connected icon
i_wifid = (0b00000, 0b10100, 0b01000, 0b10101, 0b00001, 0b00101, 0b00101, 0b10101)  # WiFi disconnected icon
i_usd   = (0b00000, 0b00000, 0b11111, 0b10001, 0b11111, 0b10001, 0b10011, 0b11110)  # uSD card icon
i_rain  = (0b00000, 0b00000, 0b00110, 0b01001, 0b11111, 0b00000, 0b10101, 0b10101)  # Rain icon
i_conn  = (0b00000, 0b00000, 0b00111, 0b00011, 0b00101, 0b01000, 0b10000, 0b00000)  # Connect icon
i_rext  = (0b00000, 0b00000, 0b00000, 0b10001, 0b01011, 0b00101, 0b01001, 0b11110)  # Remote extension icon
i_flow  = (0b00000, 0b00000, 0b00000, 0b11010, 0b10010, 0b11010, 0b10011, 0b00000)  # Flow sensor icon
i_psw   = (0b00000, 0b11100, 0b10100, 0b11100, 0b10010, 0b10110, 0b00010, 0b00111)  # Program switch icon

lcd.create_char(0, i_wific)
lcd.create_char(1, i_wifid)
lcd.create_char(2, i_usd)
lcd.create_char(3, i_rain)
lcd.create_char(4, i_conn)
lcd.create_char(5, i_rext)
lcd.create_char(6, i_flow)
lcd.create_char(7, i_psw)

# === Setup MQTT client, actions ===
client = mqtt.Client('ospilcd')  
client.on_connect = mqtt_connect  
client.on_message = mqtt_message  
client.connect(mqttAddress, mqttPort, 60)
client.loop_forever()