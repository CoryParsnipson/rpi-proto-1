BQ17441 bash library
====================

This is a small set of functions to let you interface with the BQ27441 fuel
gauge through I2C.

Usage
-----

```
source bq27441 <i2c bus id> <fuel gauge i2c address>
```

e.g.)

```
  #> source bq27441 1 0x55
  #> get_battery_percentage
  #> 27
```

Prerequisites
-------------

```
  sudo apt-get install i2c-tools
  sudo apt-get install bc
```

Block Data Configuration
------------------------

Certain commands require you to put the device into a special "config update"
mode, unseal it, and configure block data access. This is all done with the
`enter_extended_mode` command. Use the corresponding `exit_extended_mode`
command to undo the special device access modes. This is important to
remember for writes especially because they do not get finalized back to
storage until the exit command is issued and the device has gone through
soft reset.

E.g.)

```
  source bq27441_lib.sh 1 0x55

  enter_extended_mode # will print to stderr and return non-zero status if fails
  
  read_block_data 0x52 0x0A 2
  # etc

  exit_extended_mode
```
