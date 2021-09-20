#!/bin/bash

I2C_BUS_ID="${1:-1}"
I2C_DEVICE_ID="${2:-0x55}"

source bq27441_lib.sh $I2C_BUS_ID $I2C_DEVICE_ID

read_opconfig true
