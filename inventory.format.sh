#!/bin/sh

SRCFILE="mail.machines.lastinventory"

awk '
/^TARGET/ {printf "\n,"; i=1}
{ if (i%2 == 0) {
    if (LAST == "MEMORY" || LAST == "DISKSPACE-LOCAL") { 
      printf $1/1024","
    } 
    else { 
      if (LAST == "PSRSPEED") { printf $1"," }
      else { printf $0"," }
    }
  }
  else {
    LAST=$1
  }
  i++
}' $SRCFILE | 

# Originally:
#  1 - System Type  # not present, collected manually
#  2 - Target Name
#  3 - System Name
#  4 - OS version
#  5 - RAM Storage in GB
#  6 - CPU type
#  7 - CPU Speed in MHz
#  8 - # of CPU
#  9 - Int disk in GB
awk -F, '{
  printf FS      # FS is just the current Field Separator
  printf $3 FS   # the name the system uses
  printf $4 FS
  printf $8 FS
  printf $7 FS
  printf $6 FS
  printf $5 FS
  print $9 FS
}'
