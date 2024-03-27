import utime
import micropython
from machine import Pin,SoftI2C
import time
from qma7981 import QMA7981

micropython.alloc_emergency_exception_buf(100)

i2c = SoftI2C(scl=Pin(7),sda=Pin(6),freq=500000)
qma7981 = QMA7981(i2c)

print("QMA7981 id: " + hex(qma7981.whoami))

while True:
    print(qma7981.acceleration)
    utime.sleep_ms(1000)