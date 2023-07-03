from machine import UART
import machine
import utime
from umqttsimple import MQTTClient
import ujson
import ubinascii
import uasyncio

class PM25:
    def __init__(self, sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type):
        self.mqtt_server = mqtt_server
        self.client_id = ubinascii.hexlify(machine.unique_id()) # create a random client_id
        self.topic_sub = topic_sub # your desired topic for subs
        self.topic_pub = topic_pub # your desired topic for pubs
        self.last_message = 0 # for calculate last time of interval
        self.message_interval = 10 # in seconds using time.time()
        self.counter = 0
        self.uart = UART(2, 9600, timeout=1000)
        self.sensor_type = sensor_type

        try:
            self.client = self.connect_and_subscribe()
        except OSError as e:
            self.restart_and_reconnect()

    def sub_cb(self, topic, msg):
        if topic == b"server" and msg == b"download_scripts":
            print("updating code...")
            from ota import download_file
            download_file(self.sensor_type)

    def connect_and_subscribe(self):
        self.client = MQTTClient(self.client_id, self.mqtt_server)
        self.client.set_callback(self.sub_cb)
        self.client.connect()
        self.client.subscribe(self.topic_sub)
        print('Connected to %s MQTT broker, subscribed to %s topic' % (self.mqtt_server, self.topic_sub))
        return self.client

    def restart_and_reconnect(self):
        print('Failed to connect to MQTT broker. Reconnecting...')
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
                    try:
                        data = self.uart.read(32)
                        if data[0] == 66 and data[1] == 77:
                            suma = 0
                            for a in range(30):
                                suma += data[a]
                            if suma == data[30] * 256 + data[31]:
                                PM25 = int(data[6] * 256 + data[7])
                                PM10 = int(data[8] * 256 + data[9]) / 0.75
                                ujson_msg = {
                                    "PM25": round(PM25, 2),
                                    "PM10": round(PM10, 2)
                                }
                                print(f"PM25: {round(PM25, 2)} ug/m3")
                                print(f"PM10: {round(PM10, 2)} ug/m3")
                                msg_string = ujson.dumps(ujson_msg)
                                self.client.publish(self.topic_pub, msg_string)
                                self.last_message = utime.time()
                            else:
                                print("no data")
                        else:
                            print("no data")
                            self.restart_and_reconnect()
                    except BaseException as e:
                        err_msg = {
                            "PM25": "PM25",
                            "PM10": "PM10",
                            "error": e
                        }
                        print(err_msg)
                        err_msg_json = ujson.dumps(err_msg)
                        self.client.publish(self.topic_pub, err_msg_json)
                        self.restart_and_reconnect()
            except BaseException:
                print('Failed to connect to MQTT broker. Reconnecting...')
                self.restart_and_reconnect()

    async def run_async(self):
        await uasyncio.gather(self.reboot_cronjob(), self.run())

def start(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type):
    pm25 = PM25(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type)
    uasyncio.run(pm25.run_async())
