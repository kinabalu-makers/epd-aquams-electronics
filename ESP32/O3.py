# -*- coding:utf-8 -*-
"""!
  @file get_ozone_data.py
  @brief Reading ozone concentration, A concentration of one part per billion (PPB).
  @n step: we must first determine the iic device address, will dial the code switch A0, A1 (OZONE_ADDRESS_0 for [0 0]), (OZONE_ADDRESS_1 for [1 0]), (OZONE_ADDRESS_2 for [0 1]), (OZONE_ADDRESS_3 for [1 1]).
  @n       Then configure the mode of active and passive acquisition, Finally, ozone data can be read.
  @n note: it takes utime to stable oxygen concentration, about 3 minutes.
  @copyright Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
  @license The MIT License (MIT)
  @author [ZhixinLiu](zhixin.liu@dfrobot.com)
  @version V1.0
  @date 2020-5-27
  @url https://github.com/DFRobot/DFRobot_Ozone
"""
import uasyncio
import machine
import ubinascii
import ujson
import utime
from uDFRobot_Ozone import *
from umqttsimple import MQTTClient

COLLECT_NUMBER = 20  # collect number, the collection range is 1-100
IIC_MODE = 0x01  # default use IIC1

try:
    """
       The first  parameter is to select i2c0 or i2c1
       The second parameter is the i2c device address
       The default address for i2c is OZONE_ADDRESS_3
          OZONE_ADDRESS_0        0x70
          OZONE_ADDRESS_1        0x71
          OZONE_ADDRESS_2        0x72
          OZONE_ADDRESS_3        0x73
    """
    ozone = DFRobot_Ozone_IIC(IIC_MODE, OZONE_ADDRESS_3)
    """
      The module is configured in automatic mode or passive
        MEASURE_MODE_AUTOMATIC  active  mode
        MEASURE_MODE_PASSIVE    passive mode
    """
    ozone.set_mode(MEASURE_MODE_AUTOMATIC)
except BaseException as e:
    print("Sensors not connected or broken")
    utime.sleep(10)
    machine.reset()

class O3_sensor:
    def __init__(self, sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type):
        self.mqtt_server = mqtt_server
        self.sensor_ip = sensor_ip
        self.client_id = ubinascii.hexlify(machine.unique_id()) # create a random client_id
        self.topic_sub = topic_sub # your desired topic for subs
        self.topic_pub = topic_pub # your desired topic for pubs
        self.sensor_type = sensor_type

        self.last_message = 0  # for calculate last time of interval
        self.message_interval = 10  # in seconds using time.time()
        self.counter = 0
        try:
            self.client = self.connect_and_subscribe()
        except BaseException as e:
            self.restart_and_reconnect()

    def sub_cb(self, topic, msg):
        if topic == b"server" and msg == b"download_scripts":
            print("updating code...")
            from ota import download_file
            download_file()
        if topic == b"server" and msg == b"download_configs":
            print("updating configs...")
            from ota import download_config
            download_config(self.sensor_type)

    def connect_and_subscribe(self):
        self.client = MQTTClient(self.client_id, self.mqtt_server)
        self.client.set_callback(self.sub_cb)
        self.client.connect()
        self.client.subscribe(self.topic_sub)
        print(
            "Connected to %s MQTT broker, subscribed to %s topic" % (self.mqtt_server, self.topic_sub)
        )
        return self.client
    def restart_and_reconnect(self):
        print("Failed to connect to MQTT broker. Reconnecting...")
        utime.sleep(10)
        machine.reset()

    async def reboot_cronjob(self):
        """ hard reset the ESP32 for every 24 hours at 00:00:00 """
        while True:
            await uasyncio.sleep(1)
            try:
                rtc = machine.RTC()
                """ the RTC will sync when there is has internet connection """
                current_datetime = rtc.datetime() # format is (year, month, day, weekday, hours, minutes, seconds, subseconds)
                if current_datetime[4] == 0 and current_datetime[5] == 0 and current_datetime[6] == 0:
                    print("reboot every 24 hours")
                    machine.reset()
            except BaseException as e:
                print("name resolution failed", e)
    
    async def run(self):
        while True:
            await uasyncio.sleep(1)
            try:
                self.client.check_msg()
                if (utime.time() - self.last_message) > self.message_interval:
                    """Smooth data collection the collection range is 1-100"""
                    try:
                        ozone_concentration = ozone.get_ozone_data(COLLECT_NUMBER)
                        print("Ozone concentration is %d PPM." % ozone_concentration)
                        msg_string = f"{round(ozone_concentration, 0)} PPM"
                        self.client.publish(self.topic_pub, msg_string)
                    except BaseException as error:
                        err_message = {
                            "ozone_concentration": msg_string,
                            "error": error
                        }
                        print("error:", err_message)
                        msg_string = ujson.dumps(err_message)
                        self.client.publish(self.topic_pub, msg_string)
                        msg_string = ""
                        err_message = {
                            "ozone_concentration": None,
                            "error": None
                        }
                    self.last_message = utime.time()
            except BaseException as e:
                print("error:", e)
                self.restart_and_reconnect()

    async def run_async(self):
        await uasyncio.gather(self.reboot_cronjob(), self.run())
        
def start(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type):
    O3 = O3_sensor(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type)
    uasyncio.run(O3.run_async())
