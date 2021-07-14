#!/usr/bin/python
# Energymeter puls reader to MQTT for Raspberry PI
# by Anton Gustafsson
# 2013-09-20

import RPi.GPIO as GPIO
from time import gmtime, strftime, time, localtime, mktime, strptime
import json
import urllib2
import base64
from math import fabs, isnan
import paho.mqtt.client as mqtt
import os
import json


config = {
    'mqtt_host': os.environ.get('MQTT','192.168.178.2'),
    'mqtt_user': os.environ.get('MQTT_USER',None),
    'mqtt_pass': os.environ.get('MQTT_PASS',None),
    'mqtt_prefix': os.environ.get('MQTT_PREFIX','WP'),
    'mqtt_client': os.environ.get('MQTT_CLIENT','S0meter'),
    'pin': int(os.environ.get('EMM_GPIO_PIN',23)),
    'factor': float(os.environ.get('EMM_PULSE_FACTOR',1)),
    'debug': float(os.environ.get('EMM_DEBUG',False))

}


def CurrentTime():
    return strftime("%Y-%m-%d %H:%M:%S", localtime())


class EnergyLogger(mqtt.Client):
    def __init__(self,pin=config['pin'],user = config['mqtt_user'], password=config['mqtt_pass'],server = config['mqtt_host'], prefix = config['mqtt_prefix'],client = config['mqtt_client'],
                        factor = config['factor'],debug = config['debug']):

        self.factor = factor # kWh per pulse
        self.pin = pin
        self.debug = debug
        self.prefix = prefix

        self.max_send_freq = 10.0
        self.prev_pulse = 0.0
        self.EnergyCounter = 0
        self.TotalEnergy = 0
        self.HeatingEnergy = 0
        self.WaterEnergy = 0
        self.Heating = True
        self.timer = []

        #Init and connect to MQTT server
        mqtt.Client.__init__(self,client)
        self.will_set( topic = "system/" + self.prefix, payload="Offline", qos=1, retain=True)

        if user != None:
            self.username_pw_set(user,password)

        self.on_connect = self.mqtt_on_connect
        self.on_message = self.mqtt_on_message

        self.connect(server,keepalive=10)
        self.publish(topic = "system/"+ self.prefix, payload="Online", qos=1, retain=True)

        GPIO.setmode(GPIO.BCM)

        # GPIO self.pin set up as inputs, pulled up to avoid false detection.
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.add_event_detect(self.pin, GPIO.FALLING, callback=self.edge_detected, bouncetime=30)

        # when a falling or rising edge is detected on port self.pin, call callback2
        #GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self.my_callback2, bouncetime=0)

        self.loop_start()
        return

    def edge_detected(self,test):
        now = time()
        Period = now - self.prev_pulse
        if Period > 3600:
            self.prev_pulse = now
            return
       
        if Period < 0.3:
            return

    	self.timer.append(Period)
        self.EnergyCounter += 1
        Energy = self.EnergyCounter * self.factor
        self.TotalEnergy += 1
        if self.Heating == True:
            self.HeatingEnergy += 1
        if self.Heating == False: 
            self.WaterEnergy += 1

        print("%.2f period, %.0f Energy, %.0f TotalEnergy" % (Period, Energy, self.TotalEnergy))
        #Store for future reference
        self.prev_pulse = now
#        print("%.2f av_period" % (sum(self.timer))) 
        if sum(self.timer) > 10:
            av_period = sum(self.timer)/len(self.timer)
            #Calculate power and energy values.
            Power = self.factor / (av_period / 3600.0) # The energy divided on the time in hours.
            self.timer = []
            self.EnergyCounter = 0
#        if self.debug:
#            print "EnergyCounter %i Period is: %.2f s \tPower is: %.2f W\tEnergy: %.2f kWh\tChange: %.2f " % (self.EnergyCounter,Period,Power,Energy,Delta)

            self.SendMeterEvent(str(Power),str(self.TotalEnergy),str(self.HeatingEnergy),str(self.WaterEnergy))

        return


    def SendMeterEvent(self,power,energy,heating,water):

        topic = self.prefix+"/meterevent"

        msg = json.dumps({"power":power,"energy":energy,"heating":heating,"water":water})

        self.publish(topic,msg,1)

        return


    def mqtt_on_connect(self, client, userdata, flags, rc):
        print "INFO: MQTT connected!"
        self.subscribe("Verwarming/heating/State", 0)

    def mqtt_on_message(self, client, userdata, msg):
        if msg.topic == "Verwarming/heating/State":
            if str(msg.payload) == "1":
                self.Heating = True
            else:
                self.Heating = False
        #if self.debug:
        print("INFO: RECIEVED MQTT MESSAGE: "+msg.topic + " " + str(msg.payload))

        return


if __name__ == "__main__":


    #raw_input("Press Enter when ready\n>")


    print("_________________________________")
    print("Starting pulse detection")
    print("_________________________________")
    print("Time: %.2f" % time())
        #print("Factor: %f" % self.Factor)

    print("CONFIG:")

    print(json.dumps(config, indent=2))
    print("_________________________________")

    Logger = EnergyLogger()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        GPIO.cleanup()
    
    GPIO.cleanup()
#    try:
#        while(1):
#            pass
#    except KeyboardInterrupt:
#            GPIO.cleanup()       # clean up GPIO on CTRL+C exit
#GPIO.cleanup()           # clean up GPIO on normal exit



