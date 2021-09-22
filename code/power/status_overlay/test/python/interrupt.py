#!/usr/bin/env python3

import signal
import sys
import time

import RPi.GPIO as GPIO

# board pin 29 is GPIO5
SOC_GPOUT=29

# board pin 36 is GPIO16 (this is hooked up to GPIO6 in hardware)
POWER_SWITCH_PIN=36

def on_exit(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)
    GPIO.cleanup()
    sys.exit(1)

def handle_soc_interrupt(channel):
    print("SOC event detected!")

def handle_power_button_interrupt(channel):
    print("Power button press detected!")

if __name__ == '__main__':
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(SOC_GPOUT, GPIO.IN)
    GPIO.setup(POWER_SWITCH_PIN, GPIO.IN)

    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, on_exit)

    GPIO.add_event_detect(SOC_GPOUT, GPIO.FALLING, callback=handle_soc_interrupt)
    GPIO.add_event_detect(POWER_SWITCH_PIN, GPIO.FALLING, callback=handle_power_button_interrupt)

    while True:
        time.sleep(10)

# The wait_for_edge version blocks the python thread, making it unresponsive to
# keyboard and other external input until the GPIO function unblocks.
#
# def on_exit(signum, frame):
#     # restore the original signal handler as otherwise evil things will happen
#     # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
#     signal.signal(signal.SIGINT, original_sigint)
#     GPIO.cleanup()
#     sys.exit(1)
# 
# def handle_interrupt(channel):
#     print("SOC event detected!")
# 
# if __name__ == '__main__':
#     GPIO.setmode(GPIO.BOARD)
#     GPIO.setup(SOC_GPOUT, GPIO.IN)
# 
#     original_sigint = signal.getsignal(signal.SIGINT)
#     signal.signal(signal.SIGINT, on_exit)
# 
#     while True:
#         GPIO.wait_for_edge(SOC_GPOUT, GPIO.FALLING)
#         print("SOC event detected!")