#!/usr/bin/env python3

import imghdr
import os
import re
import signal
import struct
import subprocess
import sys
import time

import RPi.GPIO as GPIO

__ORIGINAL_SIGINT__=None

IMAGE_PATH = "images/"
LIB_PATH = "lib/"

PNGVIEW_PATH = "pngview"
PNGVIEW_PROCESSES = {}
DIMENSION_CACHE = {}
LAYER_DEFAULT = 15000
LAYER_BATTERY = LAYER_DEFAULT
LAYER_NUMBER = LAYER_DEFAULT
LAYER_BACKDROP = LAYER_DEFAULT - 10
DISPLAY_ID = 0

FUEL_GAUGE_SCRIPT_PATH = LIB_PATH + "bq27441_lib/"
FUEL_GAUGE_I2C_BUS_ID = 1
FUEL_GAUGE_I2C_DEVICE_ID = 0x55
FUEL_GAUGE_COMMAND = ' '.join([
    "bash",
    "-c",
    "'.",
    FUEL_GAUGE_SCRIPT_PATH + "bq27441_lib.sh",
    str(FUEL_GAUGE_I2C_BUS_ID),
    str(FUEL_GAUGE_I2C_DEVICE_ID),
    ";"
]) + " "

BATTERY_GPOUT_PIN = 29 # board pin 29 is GPIO5
BATTERY_POWER_PIN = 36 # board pin 36 is GPIO16 (tied to GPIO6 in hardware)


# -----------------------------------------------------------------------------
# Graphical utilites
# -----------------------------------------------------------------------------
def pngview(draw_id, pngfile, **kwargs):
    """ Call pngview to display an image on the screen. Returns a process id
        that the pngview call is running in.

        NOTE: it is important to properly set draw_id. This is a unique (string)
        identifier that should specify which sprite we are drawing. This is
        important because when we want to update or animation sprites, we must
        kill the previous pngview call of the sprite and then make a new one.
        Failing to keep track of draw_id properly may cause duplicates to
        appear on the script after updates and also cause memory leaks as more
        and more pngview calls add up (leading to screen de-sync).
        
        Use kwargs to set pngview parameters:

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

    pid = subprocess.Popen(pngview_call)
    time.sleep(0.025) # this is a hack to prevent flickering
    if draw_id in PNGVIEW_PROCESSES:
        PNGVIEW_PROCESSES[draw_id].kill()
    PNGVIEW_PROCESSES[draw_id] = pid

    return pid


def screen_resolution(display_id=0):
    """ Returns a pair of integers with the screen resolution of the specified
        display. The first coordinate is 'x' (screen width) and the second is
        'y' (screen height).
    """
    results = subprocess.run(["tvservice", "-s", "-v", str(display_id)], capture_output=True)
    resolution = re.search("(\d{2,}x\d{2,})", results.stdout.decode('utf-8'))

    if not resolution or results.returncode != 0:
        raise ChildProcessError("screen_resolution failed: %s" % results.stderr.decode('utf-8'))

    return [int(x) for x in resolution[0].split("x")]


def png_dimensions(fname):
    """ Returns a pair of integers that are the width and height of the image.
        This only works for PNG images.
    """
    global DIMENSION_CACHE
    if fname in DIMENSION_CACHE:
        return DIMENSION_CACHE[fname]

    with open(fname, 'rb') as fhandle:
        head = fhandle.read(24)
        if len(head) != 24:
            raise TypeError("Invalid PNG file provided: %s" % fname)
        if imghdr.what(fname) == 'png':
            check = struct.unpack('>i', head[4:8])[0]
            if check != 0x0d0a1a0a:
                raise TypeError("Invalid PNG file provided: %s" % fname)
            width, height = struct.unpack('>ii', head[16:24])
            DIMENSION_CACHE[fname] = (width, height)
            return DIMENSION_CACHE[fname]
        else:
            raise TypeError("Invalid PNG file provided: %s" % fname)


def draw_hud(**kwargs):
    """ Make all pngview calls to draw the status overlay

        battery - integer with remaining battery charge
        charging - boolean with whether or not the device is charging
    """
    if 'battery' not in kwargs:
        kwargs['battery'] = 0
    if 'charging' not in kwargs:
        kwargs['charging'] = False

    H_PADDING = 2
    V_PADDING = 2

    try:
        screen = screen_resolution()
    except ChildProcessError as e:
        print(e)
        on_exit(0, 0)

    h_cursor = screen[0]

    try:
        # draw backdrop
        backdrop_image_path = IMAGE_PATH + "backdrop.png"
        backdrop_image_dimensions = png_dimensions(backdrop_image_path)
        backdrop_pos = (screen[0] - backdrop_image_dimensions[0], 0)

        pngview("backdrop", backdrop_image_path, d=DISPLAY_ID, l=LAYER_BACKDROP, x=backdrop_pos[0], y=backdrop_pos[1])

        # draw battery in upper right corner
        battery_image_path = charge_to_img_path(kwargs['battery'], kwargs['charging'])
        battery_image_dimensions = png_dimensions(battery_image_path)

        h_cursor = h_cursor - battery_image_dimensions[0] - H_PADDING
        battery_pos = (h_cursor, V_PADDING)

        pngview("battery", battery_image_path, d=DISPLAY_ID, l=LAYER_BATTERY, x=battery_pos[0], y=battery_pos[1])

        # draw charge number
        percent_path = IMAGE_PATH + "percent.png"
        percent_dimensions = png_dimensions(percent_path)

        h_cursor = h_cursor - percent_dimensions[0] - H_PADDING
        percent_pos = (h_cursor, V_PADDING)

        pngview("percent", percent_path, d=DISPLAY_ID, l=LAYER_NUMBER, x=percent_pos[0], y=percent_pos[1])

        digit_idx = 0
        intnum = kwargs['battery']
        while True:
            digit = int(intnum % 10)
            intnum = int(intnum / 10)

            digit_image_path = IMAGE_PATH + "num" + str(digit) + ".png"
            digit_dimensions = png_dimensions(digit_image_path)

            h_cursor = h_cursor - digit_dimensions[0]
            digit_pos = (h_cursor, V_PADDING)

            pngview("digit" + str(digit_idx), digit_image_path, d=DISPLAY_ID, l=LAYER_NUMBER, x=digit_pos[0], y=digit_pos[1])
            digit_idx = digit_idx + 1

            if intnum == 0:
                break

        # remove unnecessary digits if applicable
        digit_id = "digit" + str(digit_idx)
        while digit_id in PNGVIEW_PROCESSES:
            PNGVIEW_PROCESSES[digit_id].kill()
            digit_idx = digit_idx + 1
            digit_id = "digit" + str(digit_idx)

    except TypeError as e:
        print(e)
        on_exit(0, 0)


# -----------------------------------------------------------------------------
# Battery functions
# -----------------------------------------------------------------------------
def fuel_gauge_command(func):
    """ Construct the bash script command line string to call the function
        name provided by `func`.
    """
    return FUEL_GAUGE_COMMAND + func + "'"


def get_state_of_charge():
    """ Call the bq27441 library to get the state of charge. This will
        return a string containing a base ten integer value between 0
        and 100 representing a percentage of max battery charge capacity.
    """
    result = subprocess.run(fuel_gauge_command("get_battery_percentage"), capture_output=True, shell=True)
    return int(result.stdout.decode('utf-8'))


def charge_to_img_path(charge, is_charging = False):
    """ Given a percentage of remaining battery life, return the corresponding
        image file.
    """
    battery_image_path = IMAGE_PATH + "battery"

    if charge > 95:
        charge_suffix = "100" 
    elif charge > 90:
        charge_suffix = "90"
    elif charge > 75:
        charge_suffix = "75"
    elif charge > 50:
        charge_suffix = "50"
    elif charge > 25:
        charge_suffix = "25"
    elif charge > 10:
        charge_suffix = "10"
    else:
        charge_suffix = "0"
    charge_suffix += "p"

    charging_suffix = "charging" if is_charging else ""
    battery_image_path = battery_image_path + charge_suffix + charging_suffix + ".png"
    return battery_image_path


# -----------------------------------------------------------------------------
# GPIO interrupt handling
# -----------------------------------------------------------------------------
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
    sys.exit(0)


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
    draw_hud(battery=100)

    while True:
        time.sleep(60)

    #battery = 100
    #charging = False
    #while True:
    #    draw_hud(battery=battery, charging=charging)
    #    if abs((battery - 3) % 100) > battery:
    #        charging = ~charging
    #    battery = abs((battery - 3) % 100)
    #    time.sleep(2)
