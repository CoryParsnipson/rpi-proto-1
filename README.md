# rpi-proto-1
3D printable models for RPI shell prototype

# About

The models were made in FreeCAD 0.19. The Assembly4 addon was also installed.

```
OS: Windows 10 Version 2009
Word size of OS: 64-bit
Word size of FreeCAD: 64-bit
Version: 0.19.24276 (Git)
Build type: Release
Branch: releases/FreeCAD-0-19
Hash: a88db11e0a908f6e38f92bfc5187b13ebe470438
Python version: 3.8.6+
Qt version: 5.15.1
Coin version: 4.0.1
OCC version: 7.5.0
Locale: English/United States (en_US)
```

## Functional Blocks

### dpad\_test [Status: failure (do not use)]

This is a small test swatch for metal dome switch PCB trace. This also contains wire holders on the side which (for future reference) work really well for 22 AWG solid core wire.

### dpad\_tactile [Status: success (up to date)]

This is a 3 piece jig for holding OMRON B3F-1000 tactile switches into a dpad configuration. A 2015 new nintendo 3ds XL dpad and silicon mask go on top of the cover and underneath the dpad holder.

### abxy\_tactile [Status: success (up to date)]

This is a 3 piece jig for holding OMRON B3F-1000 tactile switches into an ABXY button cross configuration. This is sized specifically for a 2015+ new Nintendo 3DS XL dpad and silicon mask.

### thumbstick [Status: obsolete]

This is designed to hold a Nintendo Switch thumbstick and (breakout board)[https://www.amazon.com/gp/product/B0191ELDL0/ref=ppx\_yo\_dt\_b\_asin\_title\_o06\_s00?ie=UTF8&psc=1] together.

### thumbstick-v2 [Status: success (up to date)]

This is designed to hold a Nintendo Switch thumbstick and (breakout board)[https://www.amazon.com/gp/product/B0191ELDL0/ref=ppx\_yo\_dt\_b\_asin\_title\_o06\_s00?ie=UTF8&psc=1] together. This version uses two pieces to hold everything in place and requires printing the top piece with supports.

### shoulder-buttons-left-v1 [Status: obsolete]

This contains a 2 piece shoulder button holder along with 2 square shoulder buttons for the left side controller. This design is not very sturdy and it is overly complicated. Not recommended.

### shoulder-buttons-left-v2 [Status: success (up to date)]

This contains a 2 piece shoulder button holder along with 2 square shoulder buttons for the left side controller. This design is sturdier than v1. This does not fit the Nintendo 3DS shoulder buttons.

### controller-chassis-mount-left [Status: success (up to date)]

This is basically thumbstick-v2, dpad\_tactile, and shoulder-buttons-left-v2 fused together into one model. This will have attachments to be fitted onto a chassis and then put inside an outer enclosure. The L1 and L2 shoulder buttons should be printed with the ironing setting enabled for best effect. The select button holder in this is barely functional. This will be improved in the next version.

### controller-chassis-mount-right [Status: success (up to date)]

This is the right controller half, meant to hold a thumbstick, ABXY buttons, and shoulder buttons in place. This isn't a symmetric version of the left controller because the thumbstick only comes in one orientation so the breakout board is mounted vertically instead of horizontally like in the left side. This makes the right controller frame slightly wider than the left side.
