#!/usr/bin/env python3

import datetime
import imghdr
import json
import os
import re
import signal
import struct
import subprocess
import sys
import threading
import time

import RPi.GPIO as GPIO


CONFIG = {}

CONFIG["CONFIG_FILE_PATH"] = "~/.status_overlay_config"

CONFIG["IMAGE_PATH"] = "images/"
CONFIG["SOUND_PATH"] = "sounds/"
CONFIG["LIB_PATH"] = "lib/"
CONFIG["PNGVIEW_PATH"] = "pngview"
CONFIG["SCREENSHOT_PATH"] = "~/screenshots"

CONFIG["LAYER_DEFAULT"] = 15000
CONFIG["LAYER_BATTERY"] = CONFIG["LAYER_DEFAULT"] + 5
CONFIG["LAYER_NUMBER"] = CONFIG["LAYER_DEFAULT"] + 10
CONFIG["LAYER_BACKDROP"] = CONFIG["LAYER_DEFAULT"] - 10
CONFIG["LAYER_NOTIFICATION"] = CONFIG["LAYER_DEFAULT"] + 15

CONFIG["DISPLAY_ID"] = 0
CONFIG["IS_VISIBLE"] = True

# INITIAL_ON -> toggle mode, start with hud visible
# INITIAL_OFF -> toggle mode, start with hud hidden
# SAVED -> toggle mode, start with state read from config file
# FLASH (show hud on button press for a short time then hide)
# FLASH_INITIAL_ON -> Flash mode with hud shown for 3 seconds on start
CONFIG["POWER_SWITCH_BEHAVIOR"] = "SAVED"

CONFIG["POWER_SWITCH_FLASH_DURATION"] = 3 # in seconds

CONFIG["FUEL_GAUGE_SCRIPT_PATH"] = CONFIG["LIB_PATH"] + "bq27441_lib/"
CONFIG["FUEL_GAUGE_I2C_BUS_ID"] = 1
CONFIG["FUEL_GAUGE_I2C_DEVICE_ID"] = 0x55

CONFIG["BATTERY_GPOUT_PIN"] = 29 # board pin 29 is GPIO5
CONFIG["BATTERY_POWER_PIN"] = 36 # board pin 36 is GPIO16 (tied to GPIO6 in hardware)

CONFIG["LOW_BATTERY_NOTIFICATION_DURATION"] = 5 # in seconds
CONFIG["CRITICAL_BATTERY_NOTIFICATION_DURATION"] = 10 # in seconds
CONFIG["LOW_BATTERY_THRESHOLD"] = 10
CONFIG["CRITICAL_BATTERY_THRESHOLD"] = 5


__ORIGINAL_SIGINT__ = None
__LAST_POWER_BUTTON_PRESSED_TIME__ = None
__PNGVIEW_PROCESSES__ = {}
__NOTIFICATION_PROCESSES__ = {}
__DIMENSION_CACHE__ = {}
__PREVIOUS_STATE_OF_CHARGE__ = 100
__SHUTDOWN_LOCK__ = threading.Lock()
__SCRIPT_PATH__ = os.path.dirname(os.path.realpath(__file__))


# -----------------------------------------------------------------------------
# Configuration utilities
# -----------------------------------------------------------------------------
def read_config_file(config_file_path):
    """ Read the config file, if it exists and update the necessary
        configuration parameters and return a dictionary with the
        configuration parameters.

        NOTE: this does not overwrite the configuration, the caller
        must do this themselves.
    """
    config_file_path = os.path.expanduser(config_file_path)
    config = CONFIG

    try:
        with open(config_file_path, 'r') as fhandle:
            serialized = ' '.join(fhandle.readlines())
            config = json.loads(serialized)
    except FileNotFoundError as e:
        print("WARNING: Could not find config file at '%s'. Using default config." % config_file_path)
        write_config_file(config_file_path)

    if config["POWER_SWITCH_BEHAVIOR"] == "INITIAL_OFF":
        config["IS_VISIBLE"] = False
    elif config["POWER_SWITCH_BEHAVIOR"] == "INITIAL_ON":
        config["IS_VISIBLE"] = True
    elif config["POWER_SWITCH_BEHAVIOR"] == "FLASH" or config["POWER_SWITCH_BEHAVIOR"] == "FLASH_INITIAL_ON":
        config["IS_VISIBLE"] = False

    return config


def write_config_file(config_file_path, write_args=CONFIG.keys()):
    """ Write the config file, writing it if it does not exist

        Caller can provide an optional list of CONFIG keys. If this
        list is not empty, only the values in the keys will be
        updated. The other values will be read from the current
        state of the config file.
    """
    config_file_path = os.path.expanduser(config_file_path)
    config = {}
    try:
        with open(config_file_path, 'r') as fhandle:
            serialized = ' '.join(fhandle.readlines())
            config = json.loads(serialized)

            for k in write_args:
                config[k] = CONFIG[k]
    except FileNotFoundError as e:
        config = CONFIG

    try:
        with open(config_file_path, 'w+') as fhandle:
            serialized = json.dumps(config, indent=2, sort_keys=True)
            fhandle.write(serialized)
    except Exception as e:
        print("Error opening config file: %s" % config_file_path)
        print(e)
        sys.exit(1)


# -----------------------------------------------------------------------------
# Graphical utilites
# -----------------------------------------------------------------------------
def pngview(draw_id, pngfile, dont_save_pid=False, **kwargs):
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
    if 'b' not in kwargs:
        kwargs['b'] = 0

    if 'n' not in kwargs:
        kwargs['n'] = ""

    pngview_call = [val for pair in zip(
        ["-" + str(k) for k in kwargs.keys()],
        [None if not str(v) else str(v) for v in kwargs.values()]
    ) for val in pair]

    pngview_call.insert(0, CONFIG["PNGVIEW_PATH"])
    pngview_call.append(pngfile)

    pngview_call = filter((None).__ne__, pngview_call)

    pid = subprocess.Popen(pngview_call)
    time.sleep(0.025) # this is a hack to prevent flickering
    if draw_id in __PNGVIEW_PROCESSES__:
        __PNGVIEW_PROCESSES__[draw_id].kill()

    if not dont_save_pid:
        __PNGVIEW_PROCESSES__[draw_id] = pid

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
    global __DIMENSION_CACHE__
    if fname in __DIMENSION_CACHE__:
        return __DIMENSION_CACHE__[fname]

    try:
        with open(fname, 'rb') as fhandle:
            head = fhandle.read(24)
            if len(head) != 24:
                raise TypeError("Invalid PNG file provided: %s" % fname)
            if imghdr.what(fname) == 'png':
                check = struct.unpack('>i', head[4:8])[0]
                if check != 0x0d0a1a0a:
                    raise TypeError("Invalid PNG file provided: %s" % fname)
                width, height = struct.unpack('>ii', head[16:24])
                __DIMENSION_CACHE__[fname] = (width, height)
                return __DIMENSION_CACHE__[fname]
            else:
                raise TypeError("Invalid PNG file provided: %s" % fname)
    except FileNotFoundError as e:
        print(e)


def set_visibility(is_visible):
    """ Set the visibility of the hud
    """
    CONFIG["IS_VISIBLE"] = is_visible
    draw_hud(battery=get_state_of_charge(), is_charging=(not is_discharging()))


def draw_hud(**kwargs):
    """ Make all pngview calls to draw the status overlay

        battery - integer with remaining battery charge
        is_charging - boolean with whether or not the device is charging
    """

    if not CONFIG["IS_VISIBLE"]:
        for v in __PNGVIEW_PROCESSES__.values():
            v.kill()
        return

    if 'battery' not in kwargs:
        kwargs['battery'] = 0
    if 'is_charging' not in kwargs:
        kwargs['is_charging'] = False

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
        backdrop_image_path = CONFIG["IMAGE_PATH"] + "backdrop.png"
        backdrop_image_dimensions = png_dimensions(backdrop_image_path)
        backdrop_pos = (screen[0] - backdrop_image_dimensions[0], 0)

        pngview(
            "backdrop",
            backdrop_image_path,
            d=CONFIG["DISPLAY_ID"],
            l=CONFIG["LAYER_BACKDROP"],
            x=backdrop_pos[0],
            y=backdrop_pos[1]
        )

        # draw battery in upper right corner
        battery_image_path = charge_to_img_path(kwargs['battery'], kwargs['is_charging'])
        battery_image_dimensions = png_dimensions(battery_image_path)

        h_cursor = h_cursor - battery_image_dimensions[0] - H_PADDING
        battery_pos = (h_cursor, V_PADDING)

        pngview(
            "battery",
            battery_image_path,
            d=CONFIG["DISPLAY_ID"],
            l=CONFIG["LAYER_BATTERY"],
            x=battery_pos[0],
            y=battery_pos[1]
        )

        # draw charge number
        percent_path = CONFIG["IMAGE_PATH"] + "percent.png"
        percent_dimensions = png_dimensions(percent_path)

        h_cursor = h_cursor - percent_dimensions[0] - H_PADDING
        percent_pos = (h_cursor, V_PADDING)

        pngview("percent", percent_path, d=CONFIG["DISPLAY_ID"], l=CONFIG["LAYER_NUMBER"], x=percent_pos[0], y=percent_pos[1])

        digit_idx = 0
        intnum = kwargs['battery']
        while True:
            digit = int(intnum % 10)
            intnum = int(intnum / 10)

            digit_image_path = CONFIG["IMAGE_PATH"] + "num" + str(digit) + ".png"
            digit_dimensions = png_dimensions(digit_image_path)

            h_cursor = h_cursor - digit_dimensions[0]
            digit_pos = (h_cursor, V_PADDING)

            pngview(
                "digit" + str(digit_idx),
                digit_image_path,
                d=CONFIG["DISPLAY_ID"],
                l=CONFIG["LAYER_NUMBER"],
                x=digit_pos[0],
                y=digit_pos[1]
            )
            digit_idx = digit_idx + 1

            if intnum == 0:
                break

        # remove unnecessary digits if applicable
        digit_id = "digit" + str(digit_idx)
        while digit_id in __PNGVIEW_PROCESSES__:
            __PNGVIEW_PROCESSES__[digit_id].kill()
            digit_idx = digit_idx + 1
            digit_id = "digit" + str(digit_idx)

    except TypeError as e:
        print(e)
        on_exit(0, 0)


def draw_notification(fname, draw_id, display_time):
    """ Draws the specified picture in the center of the screen and 
    """
    try:
        image_path = CONFIG["IMAGE_PATH"] + fname

        pid = pngview(
            draw_id,
            image_path,
            dont_save_pid=True,
            d=CONFIG["DISPLAY_ID"],
            l=CONFIG["LAYER_NOTIFICATION"]
        )

        if draw_id in __NOTIFICATION_PROCESSES__:
            __NOTIFICATION_PROCESSES__[draw_id].kill()
        __NOTIFICATION_PROCESSES__[draw_id] = pid

        helper = threading.Thread(target=__hide_notification, args=(draw_id, display_time), daemon=True)
        helper.start()
    except TypeError as e:
        print(e)
        on_exit(0, 0)


def __hide_notification(draw_id, display_time):
    """ Remove the notification at draw_id after the time specified by
        display_time has passed.
    """
    time.sleep(display_time)
    if draw_id in __NOTIFICATION_PROCESSES__:
        __NOTIFICATION_PROCESSES__[draw_id].kill()


# -----------------------------------------------------------------------------
# Sound functions
# -----------------------------------------------------------------------------
def play_sound(fname):
    """ Play a sound.
    """
    subprocess.run(["omxplayer", "--no-keys", "-o", "alsa", "--vol", "-1000", os.path.join(CONFIG["SOUND_PATH"], fname)],
        stdout=subprocess.DEVNULL)


# -----------------------------------------------------------------------------
# Battery functions
# -----------------------------------------------------------------------------
def fuel_gauge_command(func):
    """ Construct the bash script command line string to call the function
        name provided by `func`.
    """
    return ' '.join([
        "bash",
        "-c",
        "'.",
        CONFIG["FUEL_GAUGE_SCRIPT_PATH"] + "bq27441_lib.sh",
        str(CONFIG["FUEL_GAUGE_I2C_BUS_ID"]),
        str(CONFIG["FUEL_GAUGE_I2C_DEVICE_ID"]),
        ";",
        func,
        "'"
    ])


def get_state_of_charge():
    """ Call the bq27441 library to get the state of charge. This will
        return a string containing a base ten integer value between 0
        and 100 representing a percentage of max battery charge capacity.
    """
    result = subprocess.run(fuel_gauge_command("get_battery_percentage"), capture_output=True, shell=True)
    try:
        soc = int(result.stdout.decode('utf-8'))
    except ValueError as e:
        print(result)
        raise ValueError(e)
    return soc


def is_discharging():
    """ Call the bq27441 library to get whether or not the device is discharging
        battery. This will be True if the battery power is being used or False
        if the wall power is plugged in.
    """
    result = subprocess.run(fuel_gauge_command("is_discharging"), capture_output=True, shell=True)
    return result.stdout.decode('utf-8').strip() == "True"


def charge_to_img_path(charge, is_charging = False):
    """ Given a percentage of remaining battery life, return the corresponding
        image file.
    """
    battery_image_path = CONFIG["IMAGE_PATH"] + "battery"

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
    GPIO.setup(CONFIG["BATTERY_GPOUT_PIN"], GPIO.IN)
    GPIO.setup(CONFIG["BATTERY_POWER_PIN"], GPIO.IN)

    GPIO.add_event_detect(CONFIG["BATTERY_GPOUT_PIN"], GPIO.FALLING, callback=handle_battery_charge_state_change)
    GPIO.add_event_detect(CONFIG["BATTERY_POWER_PIN"], GPIO.BOTH, callback=handle_power_button_press)


def handle_battery_charge_state_change(channel):
    """ Update the status overlay with new battery life percentage
        information.
    """
    global __PREVIOUS_STATE_OF_CHARGE__

    charge = get_state_of_charge()
    is_not_charging = is_discharging()
    draw_hud(battery=charge, is_charging=(not is_not_charging))

    if is_not_charging and charge <= CONFIG["LOW_BATTERY_THRESHOLD"] and __PREVIOUS_STATE_OF_CHARGE__ > CONFIG["LOW_BATTERY_THRESHOLD"]:
        draw_notification("low_battery_warning.png", "low_battery", CONFIG["LOW_BATTERY_NOTIFICATION_DURATION"])
        play_sound("low_battery.mp3")

    if is_not_charging and charge <= CONFIG["CRITICAL_BATTERY_THRESHOLD"] and __PREVIOUS_STATE_OF_CHARGE__ > CONFIG["CRITICAL_BATTERY_THRESHOLD"]:
        __SHUTDOWN_LOCK__.release()

    __PREVIOUS_STATE_OF_CHARGE__ = charge


def handle_power_button_press(channel):
    """ Handle event where user presses down the power button.
        Momentary press should toggle status overlay visibility while a press
        longer than 2 seconds should open status overlay menu and capture
        controller input. Presses longer than 6.6 seconds will turn off the
        device in hardware.
    """
    global __LAST_POWER_BUTTON_PRESSED_TIME__
    time.sleep(0.075) # debounce

    if GPIO.input(CONFIG["BATTERY_POWER_PIN"]):
        # input is high, button was released
        release_time = datetime.datetime.now()
        if release_time - __LAST_POWER_BUTTON_PRESSED_TIME__ < datetime.timedelta(0, 0, 0, 500):
            # short press has happened
            if CONFIG["POWER_SWITCH_BEHAVIOR"] == "FLASH" or CONFIG["POWER_SWITCH_BEHAVIOR"] == "FLASH_INITIAL_ON":
                flash_behavior()
            else:
                toggle_behavior()
        else:
            # long press has happened
            screenshot_call = "raspi2png -c 9 -p " + CONFIG["SCREENSHOT_PATH"] + "/snapshot-" + \
                datetime.datetime.now().strftime("%m%d%Y-%H%M%S") + ".png"
            subprocess.Popen(screenshot_call, shell=True)
            draw_notification("snapshot_notification.png", "snapshot", 3)
    else:
        # input was low, button was pressed
        __LAST_POWER_BUTTON_PRESSED_TIME__ = datetime.datetime.now()


def toggle_behavior():
    """ Toggle the hud visibility on short press of power button
    """
    set_visibility(not CONFIG["IS_VISIBLE"])


def flash_behavior():
    """ Make the hud visible for a short time on short press of power button
    """
    if CONFIG["IS_VISIBLE"]:
        return

    set_visibility(True)
    helper = threading.Thread(target=__flash_helper, args=(CONFIG["POWER_SWITCH_FLASH_DURATION"],), daemon=True)
    helper.start()


def __flash_helper(wakeup_time):
    """ helper for flash behavior. Need to wakeup at specified time and hide hud
    """
    time.sleep(wakeup_time)
    set_visibility(False)


# -----------------------------------------------------------------------------
# System utilities
# -----------------------------------------------------------------------------
def system_setup():
    """ Add signal handlers for user keyboard interrupt and systemd termination
        interrupt.
    """
    global __ORIGINAL_SIGINT__
    __ORIGINAL_SIGINT__ = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, on_exit)

    signal.signal(signal.SIGTERM, on_exit)


def shutdown():
    """ Shut the device down.
    """
    draw_notification("critical_battery.png", "crit_battery", CONFIG["CRITICAL_BATTERY_NOTIFICATION_DURATION"])
    print("Initiating shutdown in 5 seconds...")
    play_sound("shutdown.mp3")
    time.sleep(5)
    on_exit(0, 0, False)
    subprocess.run("sudo shutdown -h now", shell=True)


def on_exit(signum, frame, perform_exit=True):
    """ Do all the cleaup needed on program exit. It is important that this
        is run every time!
    """
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, __ORIGINAL_SIGINT__)

    # release all the RPi.GPIO pins
    GPIO.cleanup()

    # kill all pngview processes
    for v in __PNGVIEW_PROCESSES__.values():
        v.kill()

    # write to config file (only want to update is_visible)
    write_config_file(CONFIG["CONFIG_FILE_PATH"], ["IS_VISIBLE"])

    if perform_exit:
        sys.exit(0)


if __name__ == '__main__':
    system_setup()
    CONFIG = read_config_file(CONFIG["CONFIG_FILE_PATH"])

    # convert all relative paths to absolute paths
    CONFIG["IMAGE_PATH"] = os.path.join(__SCRIPT_PATH__, CONFIG["IMAGE_PATH"])
    CONFIG["LIB_PATH"] = os.path.join(__SCRIPT_PATH__, CONFIG["LIB_PATH"])
    CONFIG["FUEL_GAUGE_SCRIPT_PATH"] = os.path.join(__SCRIPT_PATH__, CONFIG["FUEL_GAUGE_SCRIPT_PATH"])

    gpio_setup()
    draw_hud(battery=get_state_of_charge(), is_charging=(not is_discharging()))

    if CONFIG["POWER_SWITCH_BEHAVIOR"] == "FLASH_INITIAL_ON":
        flash_behavior()

    # acquire this twice because we want the Lock to start out blocking this thread
    __SHUTDOWN_LOCK__.acquire()
    __SHUTDOWN_LOCK__.acquire()
    shutdown()
