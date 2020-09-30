# ospiLCD-mqtt.py

This python script monitors an OpenSprinkler station and displays its status on an I2C LCD as events occur by using MQTT. It can be run on the OpenSprinkler controller itself (if it is the Pi version), or on a separate Rasperry Pi as a remote status display.

**Features:**
* 16x2 and 20x4 I2C LCDs are supported (PCF8574T based, after some changes MCP23008 is supported too)
* The first two lines are identical to LCD on OpenSprinkler 2.x (with icons)
* Third and fourth lines display information based on ospi status (remaining watering time, water level in %, E1 stations status)
* LCD updates immediately when a status change occurs on the OpenSprinkler system (e.g. a station starts/ends) without needing to poll the API.
* LCD backlight can be configured to be on all the time, or to automatically turn on when showing a new status then turn off after a configurable timeout. 
* Can be used as remote OpenSprinkler LCD display, or on a OpenSprinklerPi system. 
* Runs well on all current Raspberry Pis (2, 3, 4, Zero W)

This is based on code from Stanley's excellent build at https://github.com/stanoba/ospiLCD. Please refer to his project for designs for 3D printed case, and other build tips. This MQTT version enhahncemnt makes two important functional changes from Stanley's project:
* It subscribes to an MQTT server to receive immediate notifications of OpenSprinkler events, then uses the OpenSprinkler API to gather current data.
* Rather than a "one shot" script that runs from a cron job, this script runs ongoing in a service loop, responding to events as needed. 

_Example status, 2 line display:_ | _4 line display, built into OpenSprinkler Pi, using Stanley's build:_
---------------------------------|---------------------------------------------
![Example 2 line display](img/ospilcd5sm.jpg) | ![Example Status Display](img/ospilcd9sm.jpg)

There are two general parts to the setup, 
1. Setting up the Rasperry Pi with the LCD display and the software
2. Setting up an MQTT notifications.

# Raspberry Pi Setup and Installation


## Installing the LCD Display
Use an I2C LCD display module supported by the RPLCD library. Details about what display modules are supported, and how to wire the LCD to the Raspberry Pi are well documented in the [RPLCD library docs, here.](https://rplcd.readthedocs.io/en/stable/getting_started.html) 

If you would like to install directly onto the OpenSprinkler Rasbperry Pi, follow [Stanley's instructions, here](https://github.com/stanoba/ospiLCD.)
 

## Installing the Display Software
Starting with a recent installation of Raspbian or Raspbian Light, here are steps to install the libraries and code needed:

First, configure the Raspberry Pi to connect to your network, which needs have access to the OpenSprinkler system and the MQTT server you will be using. 

 Then use `apt` to install pip, smbus, and i2c tools:

    $ sudo apt update
    $ sudo apt upgrade -y
    $ sudo apt install python-pip python-smbus i2c-tools

Install RPLCD, netifaces, and paho-mqtt libraries directly from [PyPI](https://pypi.python.org/pypi/RPLCD/) using pip:

    $ sudo pip install RPLCD
    $ sudo pip install netifaces
    $ sudo pip install paho-mqtt
  

Install ospiLCD script from github:

    $ cd /home/pi/
    $ wget  https://raw.githubusercontent.com/sirkus7/ospiLCD-mqtt/master/ospiLCD-mqtt.py
    $ chmod +x ospiLCD-mqtt.py
    
Edit the `ospiLCD-mqtt.py` file, find the "Configuration Parameters" section near the beginning of the file, and edit the variables to fit your needs. 

# MQTT Setup
OpenSprinkler has built in support for MQTT, which is a lightweight messaging protocol used by many IoT devices to communicate status and updates. There are a number of popular cloud based MQTT services available that you could use, if you don't want to run your own. Or, you can easily run an MQTT server on your Raspberry Pi, or a Linux system on your network. 

## Install/Setup a MQTT broker (Optional)
If you would like to use a cloud based MQTT broker, skip this section and proceed to the next section. 

Install the "mosquitto" MQTT broker on your Rasbperry Pi (or another Linux system on the network.)

    $ sudo apt install mosquitto

The installation should automatically start the mosquitto MQTT broker service, as well as create service startup scripts to ensure it starts up on system boot. Quite helpful.

To double check that mosquitto process is running, you can use `ps`:

    $ ps -e | grep mosquitto 
    10806 ?        00:00:00 mosquitto


Now, you need to get the IP address of your new MQTT broker in order to tell your OpenSprinkler system where to find it. You can get this using the following command:

    $ hostname -I

Take note of the first part of the resonse, the IPv4 address of your Raspberry Pi, so you can ou'll use this to configure your OpenSprinkler system.

## Configure OpenSprinkler System to use MQTT
In the OpenSprinker UI, configure the MQTT server (broker) information. Do this by clicking on the multi square icon in the bottom right, and choosing "Edit Options", then select the "Integration" section (shown below, left). Find MQTT and click "Tap to Configure" next to it. 


1: OpenSprinkler Edit Options, Integration | 2: MQTT Settings
----------------------------------------|---------------
![Edit Options, Integration](img/OS-EditOptions.png) | ![MQTT Options](img/OS-MQTT_settings.png)

Fill in the IP address of the MQTT server (shown above, right). If you're using the mosquitto server, the default port is 1883. If your server requires username and passowrd, enter it. The default mosquitto server described above doesn't require any -- you can leave them blank.

Click submit, and return to the main screen. 

## Configure ospiLCD-mqtt.py with MQTT info
On the Raspberry Pi, edit the `ospiLCD-mqtt.py` file, end set the MQTT related settings to match those you entered into the OpenSprinkler system (server IP address and port.)
```python
    # Set MQTT info
    mqttAddress = "127.0.0.1"
    mqttPort   = "1883"
```
Note, that if you're running the MQTT server on the Raspberry Pi as we're doing here, the defaults shown above will work fine. You can use the either address identified earlier, or you can use 127.0.0.1, which points to the local Raspberry Pi. If you're using another MQTT server or cloud service, enter the address and port for that service here. 

## Run ospiLCD-mqtt.py
Now we're all ready to to run:

    $ ./ospiLCD-mqtt.py

## Troubleshooting
When `ospiLCD-mqtt.py` is run, the the LCD Screen should should light, briefly indicating it is subscribing to OpenSpinkler messages on the MQTT server:

    Connecting to
    MQTT broker...

If it cannot connect to the MQTT server, it will stay on this message indefinately. In this case, check the MQTT server settings in `ospiLCD-mqtt.py`.

If it successfully connects to the MQTT broker, It will display the following message:

    MQTT Connected
    Requesting Info

If it stays on this message now, this means it eitehr cannot successfully connect to and query the OpenSprinkler system API, or the OpenSprinkler system is not able to connect to the MQTT server. In this case, double check the MQTT server parameters in `ospiLCD-mqtt.py` and inyour OpenSprinkler system. 

If all is successful, the above messages are only shown briefly, and then the OpenSprinkler status is shown on the LCD display, such as below: 

![20x4 lcd status display](img/ospilcd5sm.jpg)



# Helpful References
* Stanley's ospiLCD project: https://github.com/stanoba/ospiLCD
* RPLCD Library Documentation: https://rplcd.readthedocs.io/en/stable/index.html
* Open Sprinkler API Documentation: https://openthings.freshdesk.com/support/solutions/articles/5000716363-os-api-documents
 