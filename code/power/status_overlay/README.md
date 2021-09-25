Status Overlay
==============

This is a group of scripts that displays an overlay on the desktop with the 
current battery level and other status information (brightness, over-temp,
under/over voltage, etc). This overlay should be able to be hidden or shown
through external input and allow the user to select certain functions like
changing brightness or turning off the system.

Prerequisites
=============

These scripts use Python3. As of the time of this writing, both Python2
and Python3 are pre-installed on Raspbian, but to make Python3 the default,
there is a manual step that must be done.

```
 # manually switch from python2 to python3

 $ sudo rm /usr/bin/python
 $ sudo ln -s /usr/bin/python3 /usr/bin/python
```
 
Install python pip.

```
  $ sudo apt-get install python3-pip
```

Install RPI.GPIO.

```
  $ sudo apt-get install python3-rpi.gpio
```

Install pngview.

```
  $ git clone --depth 1 https://github.com/AndrewFromMelbourne/raspidmx.git
  $ cd raspidmx/
  $ make -j4
  $ sudo cp pngview/pngview /usr/local/bin/
```

References
==========

[1] https://sourceforge.net/p/raspberry-gpio-python/wiki/Home/ -  RPi.GPIO documentation and examples
[2] https://github.com/d-rez/gbz\_overlay - Reference for making an RPi graphical overlay
[3] https://github.com/torfsen/python-systemd-tutorial - Adding Python script as systemd service
