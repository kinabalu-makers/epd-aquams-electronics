import uasyncio
import machine
import utime
import ubinascii
import ujson
from uDFRobot_MultiGasSensor import *
from umqttsimple import MQTTClient

I2C_1       = 0x01 # I2C_1 Use i2c1 interface (or i2c0 with configuring Raspberry Pi) to drive sensor
I2C_ADDRESS = 0x74 # I2C Device address, which can be changed by changing A1 and A0, the default address is 0x77

class MultiGas:
    def __init__(self, sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type):
        self.gas = DFRobot_MultiGasSensor_I2C(I2C_1 ,I2C_ADDRESS)
        self.mqtt_server = mqtt_server
        self.sensor_ip = sensor_ip
        self.client_id = ubinascii.hexlify(machine.unique_id()) # create a random client_id
        self.topic_sub = topic_sub # your desired topic for subs
        self.topic_pub = topic_pub # your desired topic for pubs
        self.last_message = 0 # for calculate last time of interval
        self.message_interval = 10 # in seconds using time.time()
        self.counter = 0
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
        self.gas.change_acquire_mode(self.gas.INITIATIVE)
        while True:
            await uasyncio.sleep(1)
            try:
                self.client.check_msg()
                if (utime.time() - self.last_message) > self.message_interval:
                    try:
                        if(self.gas.data_is_available() == True):
                            GasType = str(self.gas.gastype)
                            temp = str(round(self.gas.temp, 2))
                            Concentration = round(self.gas.gasconcentration,2)
                            volt_data = str(self.gas.read_volatage_data()) 
                            ujson_msg = {
                                "gasType": GasType,
                                "concentration": Concentration,
                                "temperature": temp,
                                "voltage": volt_data
                            }
                            msg_string = ujson.dumps(ujson_msg)
                            print(msg_string)
                            self.client.publish(self.topic_pub, msg_string)
                            self.last_message = utime.time()
                        else:
                            print("data is not available restarting in 10 seconds")
                            utime.sleep(10)
                            machine.reset()

                    except BaseException as e:
                        error_message = {
                            "gasType": self.gas.gastype,
                            "concentration": self.gas.gasconcentration,
                            "temperature": self.gas.temp,
                            "voltage": volt_data,
                            "error": e
                        }
                        err_msg_string = ujson.dumps(error_message)
                        print("error", err_msg_string)
                        self.client.publish(self.topic_pub, err_msg_string)
            except BaseException as e:
                print(e)
                self.restart_and_reconnect()

    async def run_async(self):
        await uasyncio.gather(self.reboot_cronjob(), self.run())
 
def start(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type):
    multi_gas = MultiGas(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type)
    uasyncio.run(multi_gas.run_async())