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

read_flags () {
  local VERBOSE="${1:-false}"

  FLAGS=$(i2c_read 0x06 w)

  if ! $VERBOSE
  then
    echo $FLAGS
  else
    if (( FLAGS & 0x0001 )); then DISCHARGING="true"  ; else DISCHARGING="false"  ; fi
    if (( FLAGS & 0x0002 )); then SOCF="true"         ; else SOCF="false"         ; fi
    if (( FLAGS & 0x0004 )); then SOC1="true"         ; else SOC1="false"         ; fi
    if (( FLAGS & 0x0008 )); then BAT_DET="true"      ; else BAT_DET="false"      ; fi

    if (( FLAGS & 0x0010 )); then CFGUPDATE="true"    ; else CFGUPDATE="false"    ; fi
    if (( FLAGS & 0x0020 )); then ITPOR="true"        ; else ITPOR="false"        ; fi
    if (( FLAGS & 0x0080 )); then OCVTAKEN="true"     ; else OCVTAKEN="false"     ; fi

    if (( FLAGS & 0x0100 )); then FASTCHARGING="true" ; else FASTCHARGING="false" ; fi
    if (( FLAGS & 0x0200 )); then FULLCHARGE="true"   ; else FULLCHARGE="false"   ; fi

    if (( FLAGS & 0x4000 )); then UNDERTEMP="true" ; else UNDERTEMP="false"; fi
    if (( FLAGS & 0x8000 )); then OVERTEMP="true" ; else OVERTEMP="false"; fi

    printf "Flags Register: 0x%04x\n" $FLAGS
    echo "------------------------"
    printf "OVER TEMP DETECTED: %s\n" $OVERTEMP
    printf "UNDER TEMP DETECTED: %s\n" $UNDERTEMP
    printf "FULL CHARGE DETECTED: %s\n" $FULLCHARGE
    printf "FAST CHARGING ENABLED: %s\n" $FASTCHARGING
    printf "OCV MEASUREMENT TAKEN: %s\n" $OCVTAKEN
    printf "POR OR RESET OCCURRED: %s\n" $ITPOR
    printf "CFG UPDATE MODE: %s\n" $CFGUPDATE
    printf "BATTERY INSERTION DETECTED: %s\n" $BAT_DET
    printf "STATE OF CHARGE < THRESHOLD 1: %s\n" $SOC1
    printf "STATE OF CHARGE < THRESHOLD F: %s\n" $SOCF
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

write_block_data_checksum () {
  if ! $EXT_MODE
  then
    echo "Can't write_block_data_checksum() while not in extended mode." >&2
  fi

  i2c_write 0x60 $1 b
}

read_block_data () {
  local SUBCLASS="${1:-0x52}" # default to "State" subclass
  local PARAMETER_OFFSET="$2"
  local DATA_LENGTH_IN_BYTES="${3:-1}"

  local BLOCK_OFFSET=$(( PARAMETER_OFFSET / 32 ))
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
    return 1
  fi

  # set subclass and block offset
  i2c_write 0x3E $SUBCLASS
  i2c_write 0x3F $BLOCK_OFFSET

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
  return 0
}

compute_block_data_checksum () {
  local SUBCLASS="${1:-0x52}" # default to "State" subclass
  local BLOCK_OFFSET="${2:-0}"

  local MAX_BLOCK_OFFSET=31

  if ! $EXT_MODE
  then
    echo "Can't compute_block_data_checksum() while not in extended mode." >&2
  fi

  local OFFSET=0
  local SUM=0

  while (( OFFSET <= MAX_BLOCK_OFFSET ))
  do
    DATA=$(read_block_data $SUBCLASS $OFFSET 1)
    SUM=$(( (SUM + DATA) % 256 ))
    OFFSET=$(( OFFSET + 1 ))
  done

  CHECKSUM=$(( 255 - SUM ))
}

write_block_data () {
  local SUBCLASS="${1:-0x52}" # default to "State" subclass
  local PARAMETER_OFFSET="$2"
  local WRITE_DATA=$3
  local DATA_LENGTH_IN_BYTES="${4:-1}"

  local BLOCK_OFFSET=$(( PARAMETER_OFFSET / 32 ))
  local WRITE_LENGTH=b

  if (( DATA_LENGTH_IN_BYTES == 2 ))
  then
    WRITE_LENGTH=w

    # need to reverse endianness of write data
    local TEMP=$(( WRITE_DATA & 0xFF ))
    WRITE_DATA=$(( (WRITE_DATA >> 8) | (TEMP << 8) ))
  fi

  if (( DATA_LENGTH_IN_BYTES > 2 ))
  then
    echo "FATAL in write_block_data(): Writing parameter longer than 2 bytes is unsupported." >&2
    return 1
  fi

  if [ -z $WRITE_DATA ]
  then
    echo "FATAL in write_block_data(): Need to supply write data." >&2
    echo "Supplied write data: " $WRITE_DATA >&2
  fi

  if ! $EXT_MODE
  then
    echo "Can't read_block_data() while not in extended mode." >&2
    return 1
  fi

  # set subclass and block offset
  i2c_write 0x3E $SUBCLASS
  i2c_write 0x3F $BLOCK_OFFSET

  local PARAMETER_ADDR=$(( 0x40 + (PARAMETER_OFFSET % 32) ))
  OLD_DATA=$(read_block_data $SUBCLASS $PARAMETER_OFFSET $DATA_LENGTH_IN_BYTES)
  CHECKSUM=$(read_block_data_checksum)

  # need to update the checksum with the delta of the new data
  CHECKSUM=$(( (255 - CHECKSUM - (OLD_DATA & 0x00FF) - ((OLD_DATA >> 8) & 0x00FF)) & 0x00FF ))
  CHECKSUM=$(( 255 - ((CHECKSUM + ((WRITE_DATA >> 8) & 0x00FF) + (WRITE_DATA & 0x00FF)) & 0x00FF) ))

  i2c_write $PARAMETER_ADDR $WRITE_DATA $WRITE_LENGTH
  write_block_data_checksum $CHECKSUM
}

get_battery_percentage () {
  printf "%d\n" $(i2c_read 0x1C w)
}

get_temperature () {
  local UNIT="${1:-f}" # select Fahrenheit (f), Celsius (c), or Kelvin (k)

  TEMP=$(i2c_read 0x02 w)
  CONVERTED_TEMP=0

  case $UNIT in
    "k") CONVERTED_TEMP=$(( TEMP / 10 )) ;;
    "c") CONVERTED_TEMP=$(( (TEMP / 10) - 273 )) ;;
    *)   CONVERTED_TEMP=$(( ((TEMP / 10) - 273) * 9 / 5 + 32 )) ;;
  esac

  echo $CONVERTED_TEMP
}

get_voltage () {
  MILLIVOLTS=$(i2c_read 0x04 w)
  echo $(( MILLIVOLTS / 1000 ))
}
