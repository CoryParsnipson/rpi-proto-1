#!/bin/bash

I2C_BUS_ID="${1:-1}"
I2C_DEVICE_ID="${2:-0x55}"

source bq27441_lib.sh $I2C_BUS_ID $I2C_DEVICE_ID

enter_extended_mode

BLOCKDATA=$(read_block_data 0x52 0x0A 2)
printf "DESIGN CAPACITY: %d mAh\n" $BLOCKDATA

BLOCKDATA=$(read_block_data 0x52 12 2)
printf "DESIGN ENERGY: %d mWh\n" $BLOCKDATA

BLOCKDATA=$(read_block_data 0x52 0x10 2)
printf "TERMINATE VOLTAGE: %d mV\n" $BLOCKDATA

BLOCKDATA=$(read_block_data 0x52 27 2)
printf "TAPER RATE: %d [0.1 Hr rate]\n" $BLOCKDATA

BLOCKDATA=$(read_block_data 0x52 26 1)
printf "SOCI DELTA: %d percent\n" $BLOCKDATA

exit_extended_mode
read_control_status true
