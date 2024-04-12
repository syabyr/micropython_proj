import utime
import micropython
from machine import Pin,SoftI2C
import time
from qma7981 import QMA7981
from umqtt.simple import MQTTClient

# mqtt client setup
CLIENT_NAME = 'blue'
BROKER_ADDR = '202.1.1.1'
mqttc = MQTTClient(CLIENT_NAME, BROKER_ADDR, keepalive=60)
mqttc.connect()

X_TOPIC=b'acc/x'
Y_TOPIC=b'acc/y'
Z_TOPIC=b'acc/z'

micropython.alloc_emergency_exception_buf(100)

i2c = SoftI2C(scl=Pin(7),sda=Pin(6),freq=500000)
qma7981 = QMA7981(i2c)

print("QMA7981 id: " + hex(qma7981.whoami))

while True:
    value = qma7981.acceleration
    print(value)
    mqttc.publish(X_TOPIC,str(value[0]).encode())
    mqttc.publish(Y_TOPIC,str(value[1]).encode())
    mqttc.publish(Z_TOPIC,str(value[2]).encode())
    utime.sleep_ms(50)
