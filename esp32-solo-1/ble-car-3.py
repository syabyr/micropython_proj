import ubluetooth
from machine import Pin, PWM
import time

# 电机引脚配置
motor_a_pwm = PWM(Pin(12), freq=1000, duty=0)  # 电机A PWM
motor_a_in1 = Pin(14, Pin.OUT)  # 电机A方向控制1
motor_a_in2 = Pin(27, Pin.OUT)  # 电机A方向控制2

motor_b_pwm = PWM(Pin(13), freq=1000, duty=0)  # 电机B PWM
motor_b_in1 = Pin(26, Pin.OUT)  # 电机B方向控制1
motor_b_in2 = Pin(25, Pin.OUT)  # 电机B方向控制2

led_pin = Pin(2,Pin.OUT) # blue led
# 初始化电机
def stop_motors():
    motor_a_pwm.duty(0)
    motor_b_pwm.duty(0)
    motor_a_in1.value(0)
    motor_a_in2.value(0)
    motor_b_in1.value(0)
    motor_b_in2.value(0)

def move_forward(speed):
    motor_a_pwm.duty(speed)
    motor_b_pwm.duty(speed)
    motor_a_in1.value(1)
    motor_a_in2.value(0)
    motor_b_in1.value(1)
    motor_b_in2.value(0)

def move_backward(speed):
    motor_a_pwm.duty(speed)
    motor_b_pwm.duty(speed)
    motor_a_in1.value(0)
    motor_a_in2.value(1)
    motor_b_in1.value(0)
    motor_b_in2.value(1)

def turn_left(speed):
    motor_a_pwm.duty(speed)
    motor_b_pwm.duty(speed)
    motor_a_in1.value(0)
    motor_a_in2.value(1)
    motor_b_in1.value(1)
    motor_b_in2.value(0)

def turn_right(speed):
    motor_a_pwm.duty(speed)
    motor_b_pwm.duty(speed)
    motor_a_in1.value(1)
    motor_a_in2.value(0)
    motor_b_in1.value(0)
    motor_b_in2.value(1)

# 蓝牙初始化
ble = ubluetooth.BLE()
ble.active(True)

# 定义服务UUID和特征值UUID
SERVICE_UUID = ubluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")  # 示例UUID
CHARACTERISTIC_UUID = ubluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")  # 示例UUID

# 注册服务
service = (
    SERVICE_UUID,
    [
        (CHARACTERISTIC_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE | ubluetooth.FLAG_NOTIFY),
    ],
)

services = (service,)
((char_handle,),) = ble.gatts_register_services(services)

# 蓝牙事件处理
def bt_irq(event, data):
    if event == 1:  # 蓝牙连接
        print("Connected")
        led_pin.on()
    elif event == 2:  # 蓝牙断开
        print("Disconnected")
        stop_motors()
        led_pin.off()
        start_advertising()  # 重新启动广播
    elif event == 3:  # 收到数据
        conn_handle, value_handle = data
        value = ble.gatts_read(value_handle)
        handle_control_signal(value)

# 处理控制信号
def handle_control_signal(value):
    if value == b'F':  # 前进
        move_forward(512)
    elif value == b'B':  # 后退
        move_backward(512)
    elif value == b'L':  # 左转
        turn_left(512)
    elif value == b'R':  # 右转
        turn_right(512)
    elif value == b'S':  # 停止
        stop_motors()

# 启动广播
def start_advertising():
    name = "ESP32-BLE-Car"
    adv_data = bytearray(b'\x02\x01\x06')  # 标志位
    adv_data += bytearray((len(name) + 1, 0x09)) + name.encode('utf-8')  # 设备名称
    adv_data += bytearray(b'\x03\x03\xAA\xFE')  # 添加服务UUID到广播数据中（示例UUID：0xAAFE）
    ble.gap_advertise(100000, adv_data=adv_data)
    print("Advertising started...")

# 设置蓝牙事件回调
ble.irq(bt_irq)

# 启动广播
start_advertising()

# 主循环
while True:
    time.sleep_ms(100)