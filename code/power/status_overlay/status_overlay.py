#!/usr/bin/env python3

import signal
import subprocess
import sys
import time

import RPi.GPIO as GPIO

__ORIGINAL_SIGINT__=None

PNGVIEW_PATH="pngview"
BATTERY_GPOUT_PIN=29 # board pin 29 is GPIO5
BATTERY_POWER_PIN=36 # board pin 36 is GPIO16 (tied to GPIO6 in hardware)


def pngview(pngfile, **kwargs):
    """ Call pngview to display an image on the screen. Returns a process id
        that the pngview call is running in. Use kwargs to set parameters:

        -b - set background colour 16 bit RGBA
              e.g. 0x000F is opaque black
        -d - Raspberry Pi display number
        -l - DispmanX layer number
        -x - offset (pixels from the left)
        -y - offset (pixels from the top)
        -t - timeout in ms
        -n - non-interactive mode
    """
    pngview_call = [val for pair in zip(["-" + str(k) for k in kwargs.keys()], [str(v) for v in kwargs.values()]) for val in pair]
    pngview_call.insert(0, PNGVIEW_PATH)
    pngview_call.append(pngfile)

    return subprocess.Popen(pngview_call)


def draw_status_hud():
    """ Make all pngview calls to draw the status overlay
    """
    pass


def gpio_setup():
    """ Setup for all GPIO pins
    """
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(BATTERY_GPOUT_PIN, GPIO.IN)
    GPIO.setup(BATTERY_POWER_PIN, GPIO.IN)

    global __ORIGINAL_SIGINT__
    __ORIGINAL_SIGINT__ = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, on_exit)

    GPIO.add_event_detect(BATTERY_GPOUT_PIN, GPIO.FALLING, callback=handle_battery_charge_state_change)
    GPIO.add_event_detect(BATTERY_POWER_PIN, GPIO.FALLING, callback=handle_power_button_press)


def on_exit(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, __ORIGINAL_SIGINT__)
    GPIO.cleanup()
    sys.exit(1)


def handle_battery_charge_state_change(channel):
    """ Update the status overlay with new battery life percentage
        information.
    """
    print("SOC event detected!")


def handle_power_button_press(channel):
    """ Handle event where user presses down the power button.
        Momentary press should toggle status overlay visibility while a press
        longer than 2 seconds should open status overlay menu and capture
        controller input. Presses longer than 6.6 seconds will turn off the
        device in hardware.
    """
    print("Power button event detected!")


if __name__ == '__main__':
    gpio_setup()

    while True:
        time.sleep(60)
