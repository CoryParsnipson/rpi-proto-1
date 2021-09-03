#!/bin/bash

I2C_BUS_ID="${1:-1}"
I2C_DEVICE_ID="${2:-0x55}"

source bq27441_lib.sh $I2C_BUS_ID $I2C_DEVICE_ID

enter_extended_mode

read_control_status true
read_flags true

write_block_data 0x52 10 2600 2 # write 2600 mAh to Design Capacity
write_block_data 0x52 12 9620 2 # write 9620 mW to Design Energy
write_block_data 0x52 16 3200 2 # write 3200 mV to Terminate Voltage
write_block_data 0x52 27 158  2 # write 158 [0.1 Hr rate] to Taper Rate

exit_extended_mode

# read values back
sleep 5
enter_extended_mode

BLOCKDATA=$(read_block_data 0x52 10 2)
printf "DESIGN CAPACITY: %d mAh\n" $BLOCKDATA

BLOCKDATA=$(read_block_data 0x52 12 2)
printf "DESIGN ENERGY: %d mWh\n" $BLOCKDATA

BLOCKDATA=$(read_block_data 0x52 0x10 2)
printf "TERMINATE VOLTAGE: %d mV\n" $BLOCKDATA

BLOCKDATA=$(read_block_data 0x52 27 2)
printf "TAPER RATE: %d [0.1 Hr rate]\n" $BLOCKDATA

exit_extended_mode
read_control_status true
read_flags true
