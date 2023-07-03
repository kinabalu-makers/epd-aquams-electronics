import config

mqtt_server = config.MQTT_SERVER
wifi_ssid = config.WIFI_SSID
wifi_password = config.WIFI_PASSWORD
sensor_type = config.SENSOR_TYPE
sensor_ip = config.SENSOR_IP
topic_pub = config.TOPIC_PUB
topic_sub = config.TOPIC_SUB

if sensor_type == "CO":
    print("CO")
    from MULTI_GAS import start
    start(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type)
elif sensor_type == "DHT":
    print("DHT")
    from DHT import start
    start(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type)
elif sensor_type == "NO2":
    print("NO2")
    from MULTI_GAS import start
    start(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type)
elif sensor_type == "SO2":
    print("SO2")
    from MULTI_GAS import start
    start(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type)
elif sensor_type == "PM25":
    print("PM25")
    from PM25 import start
    start(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type)
elif sensor_type == "O3":
    print("O3")
    from O3 import start
    start(sensor_ip, mqtt_server, topic_pub, topic_sub, sensor_type)