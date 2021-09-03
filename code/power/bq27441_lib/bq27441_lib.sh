#!/bin/bash

I2C_BUS=$1
DEVICE_ID=$2
if [ -z "$DEVICE_ID" ]
then
  echo "Usage: bq27441_lib [I2C_BUS_ID] [DEVICE_ID]\n"
  echo "  I2C_BUS_ID - I2C bus device to read from. E.g. 1 from /dev/i2c-1\n"
  echo "  DEVICE_ID - I2C bus address of the device to read from\n"
fi

EXT_MODE=false
EXT_MODE_SEALED=0

i2c_read () {
  local ADDR=$1
  local MODE="${2:-w}"

  i2cget -y $I2C_BUS $DEVICE_ID $ADDR $MODE
}

i2c_write () {
  local ADDR=$1
  local DATA=$2
  local MODE="${3:-b}"

  i2cset -y $I2C_BUS $DEVICE_ID $ADDR $DATA $MODE
}

wait_for_cfgupdate () {
  local TRIES=0
  local MAX_TRIES=5
  local SETCFG_BIT=0
  local IS_DONE=0
  local DESIRED_CFGUPDATE_VAL=${1:-1}

  while (( IS_DONE == 0 && TRIES < MAX_TRIES ))
  do
    SETCFG_BIT=$(i2c_read 0x06)
    if (( ((SETCFG_BIT & 0x10) >> 4) == DESIRED_CFGUPDATE_VAL ))
    then
      IS_DONE=1
      break
    else
      TRIES=$(($TRIES + 1))
    fi
    echo "Waiting for SETCFGUPDATE to be set..."
    sleep 1
  done
  
  if (( IS_DONE == 0 ))
  then
    echo "Timeout waiting for SETCFGUPDATE to be set." >&2
    return 1
  else
    return 0
  fi
}

read_control_status () {
  local VERBOSE="${1:-false}"

  i2c_write 0x00 0x0000 w
  STATUS=$(i2c_read 0x00 w)
  
  if [ "$VERBOSE" = false ]
  then
    echo $STATUS
  else
    if (( $STATUS & 0x8000 )); then SHUTDOWNEN="true" ; else SHUTDOWNEN="false" ; fi
    if (( $STATUS & 0x4000 )); then WDRESET="true"    ; else WDRESET="false"    ; fi
    if (( $STATUS & 0x2000 )); then SS="true"         ; else SS="false"         ; fi
    if (( $STATUS & 0x1000 )); then CALMODE="true"    ; else CALMODE="false"    ; fi
    if (( $STATUS & 0x0800 )); then CCA="true"        ; else CCA="false"        ; fi
    if (( $STATUS & 0x0400 )); then BCA="true"        ; else BCA="false"        ; fi
    if (( $STATUS & 0x0200 )); then QMAXUP="true"     ; else QMAXUP="false"     ; fi
    if (( $STATUS & 0x0100 )); then RESUP="true"      ; else RESUP="false"      ; fi

    if (( $STATUS & 0x0080 )); then INITCOMP="true"   ; else INITCOMP="false"   ; fi
    if (( $STATUS & 0x0040 )); then HIBERNATE="true"  ; else HIBERNATE="false"  ; fi
    if (( $STATUS & 0x0010 )); then SLEEP="true"      ; else SLEEP="false"      ; fi
    if (( $STATUS & 0x0008 )); then LDMD="true"       ; else LDMD="false"       ; fi
    if (( $STATUS & 0x0004 )); then RUPDIS="true"     ; else RUPDIS="false"     ; fi
    if (( $STATUS & 0x0002 )); then VOK="true"        ; else ROK="false"        ; fi

    printf "Control Register Status: 0x%04x\n" $STATUS
    echo "------------------------"
    printf "Shutdown Enabled: %s\n" $SHUTDOWNEN
    printf "Watchdog Reset: %s\n" $WDRESET
    printf "Sealed: %s\n" $SS
    printf "Columb Counter Auto Calibration: %s\n" $CCA
    printf "Board Calibration Routine Active: %s\n" $BCA
    printf "Qmax updated: %s\n" $QMAXUP
    printf "Resistance Updated: %s\n" $RESUP
    
    echo ""
  fi
}

## unseal the fuel gauge; returns control register status afterwards
unseal () {
  local VERBOSE="${1:-false}"

  i2c_write 0x00 0x8000 w
  i2c_write 0x00 0x8000 w

  read_control_status $VERBOSE
}

## seal the fuel gauge; returns the control register status afterwards
seal () {
  local VERBOSE="${1:-false}"

  i2c_write 0x00 0x0020 w

  read_control_status $VERBOSE
}

## populate the control status register and read it to determine if the fuel
## gauge is sealed
is_sealed () {
  STATUS=$(read_control_status)
  SEALED=$(( $STATUS & 0x2000 ))

  echo $(( SEALED >> 13 ))
}

soft_reset () {
  i2c_write 0x00 0x0042 w
}

enter_extended_mode () {
  if $EXT_MODE
  then
    echo "Already in extended mode."
    return 0
  fi

  EXT_MODE_SEALED=$(is_sealed)
  if [ -n $EXT_MODE_SEALED ]
  then
    echo "Unsealing to enter extended mode."
    unseal > /dev/null

    if (( is_sealed == 1 ))
    then
      echo "Failed to unseal device" >&2
      read_control_status true
      return 1
    fi
  fi

  # enter CFGUPDATE mode
  i2c_write 0x00 0x0013 w
  
  # wait for the cfgupdate flag to be set
  wait_for_cfgupdate
  local CFGUPDATE=$?
  if (( CFGUPDATE != 0 ))
  then
    return $CFGUPDATE
  fi

  # enable block data memory control
  i2c_write 0x61 0x00

  EXT_MODE=true
  return 0
}

exit_extended_mode () {
  if ! $EXT_MODE
  then
    echo "Not in extended mode. Exit aborted."
    return 0
  fi

  soft_reset

  wait_for_cfgupdate 0
  local CFGUPDATE=$?
  if (( CFGUPDATE != 0 ))
  then
    echo "Failed to exit config update mode" >&2
    echo $CFGUPDATE
  fi

  # reseal if sealed
  if (( EXT_MODE_SEALED != 0 ))
  then
    seal > /dev/null

    local SEALED_CHECK=$(is_sealed)
    if (( SEALED_CHECK == 0 ))
    then
      echo "Failed to seal device" >&2
      read_control_status true
      return 1
    fi
  fi

  EXT_MODE=false
  echo "Exiting extended mode."
}

read_block_data_checksum () {
  if ! $EXT_MODE
  then
    echo "Can't read_block_data_checksum() while not in extended mode." >&2
  fi

  CHECKSUM=$(i2c_read 0x60 b)
  echo $CHECKSUM
}

read_block_data () {
  local SUBCLASS="${1:-0x52}" # default to "State" subclass
  local PARAMETER_OFFSET="$2"
  local DATA_LENGTH_IN_BYTES="${3:-1}"

  local BLOCK_OFFSET=$(( $PARAMETER_OFFSET / 32 ))
  local READ_LENGTH=b
  
  if (( DATA_LENGTH_IN_BYTES == 2 ))
  then
    READ_LENGTH=w
  fi

  if (( DATA_LENGTH_IN_BYTES > 2 ))
  then
    echo "FATAL in read_block_data(): Reading parameter longer than 2 bytes is unsupported." >&2
    return 1
  fi

  if ! $EXT_MODE
  then
    echo "Can't read_block_data() while not in extended mode." >&2
  fi

  local RES=$?
  if (( RES != 0 ))
  then
    return $RES
  fi

  # set subclass and block offset
  i2c_write 0x3E $SUBCLASS
  i2c_write 0x3F $BLOCK_OFFSET

  # TODO: validate checksum

  local PARAMETER_ADDR=$(( 0x40 + (PARAMETER_OFFSET % 32) ))
  PARAMETER_DATA=$(i2c_read $PARAMETER_ADDR $READ_LENGTH)

  # if read_length > 1, need to fix endianness
  FIXED_PDATA=$PARAMETER_DATA
  if [ $READ_LENGTH = "w" ]
  then
    FIXED_PDATA=$(( PARAMETER_DATA >> 8 ))
    FIXED_PDATA=$(( ((PARAMETER_DATA & 0x00FF) << 8) | FIXED_PDATA ))
  fi

  echo $FIXED_PDATA
}
