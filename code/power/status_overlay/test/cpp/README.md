Status Overlay
==============

This is a group of scripts that displays an overlay on the desktop with the 
current battery level and other status information (brightness, over-temp,
under/over voltage, etc). This overlay should be able to be hidden or shown
through external input and allow the user to select certain functions like
changing brightness or turning off the system.

Prerequisites
=============

To interface with the GPIO pins directly, we need to install wiringPi.

```
  $ gpio -v
```

If this command doesn't work, it's not installed. Run this to install it:

```
  $ sudo apt-get install wiringpi
  $ gpio -v
  $ gpio readall
```

References
==========

[1] http://wiringpi.com/reference/priority-interrupts-and-threads/
[2] https://github.com/WiringPi/WiringPi/blob/master/examples/isr.c
