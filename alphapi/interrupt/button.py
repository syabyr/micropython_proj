from machine import Pin
from time import sleep

motion = False

def handle_interrupt(pin):
  global motion
  motion = True
  global interrupt_pin
  interrupt_pin = pin 

led = Pin(12, Pin.OUT)
pira = Pin(10, Pin.IN)
pirb = Pin(20, Pin.IN)
pirc = Pin(21, Pin.IN)


pira.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt)
pirb.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt)
pirc.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt)


while True:
  if motion:
    print('Motion detected! Interrupt caused by:', interrupt_pin)
    led.value(1)
    sleep(2)
    led.value(0)
    print('Motion stopped!')
    motion = False
