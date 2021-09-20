PiGPIO Test
===========

Test script to get an edge detection callback on GPIO6 while it is being
claimed by gpio-poweroff. PiGPIO is an alternative library to RPi.GPIO that
lets me monitor a claimed GPIO through the alternate method of polling the
pin status.

Author's note:
--------------

This library is kind of sketchy, tbh. It's very old fashioned. It uses a
polling daemon you need sudo permissions and you have to set it up before
running the script. Also, ignoring the synchronization primitives on the GPIO
pins is kind of a bad idea, but for this specific use-case we should be good
because I only need to read from the pin.

Prerequisites:
==============

Install pigpio:

```
  $ sudo apt-get install pigpio python3-pigpio
```

Start the daemon:

```
  $ sudo pigpiod -s 10
```

Then run the script.

References
==========

[1] https://abyz.me.uk/rpi/pigpio/
