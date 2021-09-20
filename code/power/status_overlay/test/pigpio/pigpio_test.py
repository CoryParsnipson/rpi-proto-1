#!/usr/bin/python

import pigpio
import time

POWER_SWITCH_GPIO=6

def cb(gpio, level, tick):
    print("GPIO%d triggered!" % gpio)

if __name__ == '__main__':
    pi = pigpio.pi()
    if not pi.connected:
        print("Not connected to PIGPIO Daemon")

    cb1 = pi.callback(POWER_SWITCH_GPIO, pigpio.FALLING_EDGE, cb)

    while (True):
        time.sleep(10)
