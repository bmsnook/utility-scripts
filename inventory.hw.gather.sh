#!/bin/sh

## So, for each server, we want to find out:
##     - Architecture and model
##     - Disks in service and size
##     - number and speed of cpu
##     - amount of memory
##     - number of network cards
## The following files should be what we want to look at:
##     /ms/logs/users/pedrick/spares/machines
##     /ms/logs/users/pedrick/spares/machines_dialup
##     /ms/logs/users/pedrick/spares/machines_internal
##     /ms/logs/users/pedrick/spares/machines_webhost
## This script:
##     /ms/logs/users/bmsnook/bin/inventory.hw.gather.sh
## Results go to 
##     /ms/logs/users/bmsnook/inventory/hw/
## 
## For each server, we want something like:
##     Hostname: carlin.mail.atl.earthlink.net
##     Arch: SunOS
##     Model: SUNW,Sun-Fire-280R
##     Disk:       0. c0t0d0 <SUN36G cyl 24620 alt 2 hd 27 sec 107>
##     Disk:       1. c0t1d0 <SUN36G cyl 24620 alt 2 hd 27 sec 107>
##     CPU: 1002 MHz,
##     CPU: 1002 MHz,
##     Memory size: 2048 Megabytes
##     Network: bge
##     Network: bge0
##     Network: bge1
##     Network: bge2
##     Network: bge3
## 

## Locate binaries:
## Locate AWK
if [ -r /bin/nawk ]; then
  AWK=/bin/nawk
elif [ -r /bin/awk ]; then
  AWK=/bin/awk
elif [ -r /usr/bin/awk ]; then
  AWK=/usr/bin/awk
  else
    echo "ERROR: Couldn't find 'awk'"
    return 0
fi
export AWK

## Locate Netstat
if [ -r /bin/netstat ]; then 
  NETSTAT=/bin/netstat
elif [ -r /usr/sbin/netstat ]; then 
  NETSTAT=/usr/sbin/netstat
  elif [ -r /usr/bin/netstat ]; then
    NETSTAT=/usr/bin/netstat
  else 
    echo "ERROR: Couldn't find 'netstat'"
    return 0
fi
export NETSTAT

## Locate Uname
if [ -r /sbin/uname ]; then
  UNAME=/sbin/uname
elif [ -r /bin/uname ]; then
  UNAME=/bin/uname
  elif [ -r /usr/bin/uname ]; then
    UNAME=/usr/bin/uname
  else
    echo "ERROR: Couldn't find 'uname'"
    return 0
fi
export UNAME

## Locate Ifconfig
if [ -r /sbin/ifconfig ]; then
  IFCONFIG=/sbin/ifconfig
elif [ -r /usr/sbin/ifconfig ]; then
  IFCONFIG=/usr/sbin/ifconfig
  else
    echo "ERROR: Couldn't find 'ifconfig'"
    return 0
fi
export IFCONFIG

DISKLABEL=/sbin/disklabel
UERF=/usr/sbin/uerf
PSRINFO=/usr/sbin/psrinfo
IOSTAT=/bin/iostat
PRTCONF=/usr/sbin/prtconf
FORMAT=/usr/sbin/format
export DISKLABEL UERF PSRINFO IOSTAT PRTCONF FORMAT

THISSYS=`${UNAME} -n`
THISOS=`${UNAME} -s`
export THISSYS THISOS


## Gather data with:
## Name, arch and model:
##     uname -a | ${AWK} '{print $2"\nArch: "$1"\nModel: "$NF }'

#${UNAME} -a | ${AWK} '{print $2"\nArch: "$1"\nModel: "$NF }'
${UNAME} -n
${UNAME} -p | ${AWK} '{printf "Arch: %s\n",$0}'
${UNAME} -a | ${AWK} '{printf "Model: %s\n",$NF}'
${UNAME} -s | ${AWK} '{printf "OS: %s\n",$0}'
if [ "x$THISOS" = "xOSF1" -o "x$THISOS" = "xSunOS" ]; then
${UNAME} -v | ${AWK} '{printf "OSREV: %s\n",$0}'
fi
if [ "x$THISOS" = "xFreeBSD" ]; then
${UNAME} -v | ${AWK} '{printf "OSREV: %s %s\n",$2,$NF}'
fi

## 
## Disk sizes:
##     echo 0 | format | grep c.t.d.
## 
#/bin/echo 0 | format | ${AWK} '/ c.t.d. /{printf "Disk: %s\n",$0}'
## 
## Disk manufacturer/model:
##     iostat -En
## 
## c0t6d0      Soft Errors: 0 Hard Errors: 0 Transport Errors: 0 
## Vendor: TOSHIBA  Product: DVD-ROM SD-M1401 Revision: 1009 Serial No: 12/20/00 
## Size: 18446744073.71GB <-1 bytes>
## Media Error: 0 Device Not Ready: 0 No Device: 0 Recoverable: 0 
## Illegal Request: 0 Predictive Failure Analysis: 0 
## c1t0d0          Soft Errors: 0 Hard Errors: 0 Transport Errors: 0 
## Vendor: SEAGATE  Product: ST318304FSUN18G  Revision: A42D Serial No: 0101L08TEL 
## Size: 18.11GB <18110967808 bytes>
## Media Error: 0 Device Not Ready: 0 No Device: 0 Recoverable: 0 
## Illegal Request: 0 Predictive Failure Analysis: 0
## Bonnie/Clyde:
## c0t0d0          Soft Errors: 0 Hard Errors: 0 Transport Errors: 0 
## Vendor: SEAGATE  Product: ST32550W SUN2.1G Revision: 0418 Serial No: 05118522 
## RPM: 5400 Heads: 19 Size: 2.13GB <2127708160 bytes>
## Media Error: 0 Device Not Ready: 0 No Device: 0 Recoverable: 0 
## Illegal Request: 0 Predictive Failure Analysis: 0

if [ "x$THISOS" = "xSunOS" ]; then 
(${IOSTAT} -En || echo 0 | ${FORMAT}) | ${AWK} '
/^[A-z]/&&/[Ee]rrors/{ddev=$1; \
 getline;dvend=$2;dprod=$4; \
 getline;for(i=1;i<NF;i++){if($i~/Size/){dsize=$(i+1)}};
 getline;
 getline;
 if(dprod !~ /ROM/){
   printf "Disk: %s  mfg: %s  model: %s  size: %s\n",ddev,dvend,dprod,dsize
 }
}
/ c.t.d. /{
  printf "Disk: %s\n",$0
}
'
fi

if [ "x$THISOS" = "xOSF1" ]; then
for each_drive in `
  ${AWK} '/\/dev\//{
    snum=split($1,dpath,"/");
    epath=substr(dpath[snum],1,length(dpath[snum])-1);
    if(epath in all_devs)
      {}
    else{
      all_devs[epath]
    }
  }END{
    for(each_dev in all_devs){printf "/dev/r%sc\n",each_dev}
  }' /etc/fstab`
do
  ${DISKLABEL} -r $each_drive | $AWK '
  /^# \/dev/{ddev=substr($2,1,length($2)-1)}
  /^type/{dtype=$0}
  /^bytes/{dbps=$2}
  /^rpm/{drpm=$0}
  /^  c:/{dsize=$2}
  END{
    printf "Disk: %s  %s  %s  %s sectors (%.2f GB)\n",ddev,dtype,drpm,dsize,((dbps/1024)*dsize/(1024*1024))
  }'
done
fi

if [ "x$THISOS" = "xFreeBSD" ]; then
for each_drive in `
  ${AWK} '/\/dev\//&&!/cd/{
    snum=split($1,dpath,"/");
    epath=substr(dpath[snum],1,length(dpath[snum])-1);
    if(epath in all_devs)
      {}
    else{
      all_devs[epath]
    }
  }END{
#    for(each_dev in all_devs){printf "/dev/r%sc\n",each_dev}
    for(each_dev in all_devs){printf "%s\n",each_dev}
  }' /etc/fstab`
do
  ${DISKLABEL} -r $each_drive | $AWK '
  /^# \/dev/{ddev=substr($2,1,length($2)-1)}
  /^type/{dtype=$0}
  /^bytes/{dbps=$2}
  /^rpm/{drpm=$0}
  /^  c:/{dsize=$2}
  END{
    printf "Disk: %s  %s  %s  %s sectors (%.2f GB)\n",ddev,dtype,drpm,dsize,((dbps/1024)*dsize/(1024*1024))
  }'
done
fi

## 
## CPU info:
## 

if [ "x$THISOS" = "xOSF1" -o "x$THISOS" = "xSunOS" ]; then
${PSRINFO} -v | ${AWK} '
/^  The/{printf "CPU: %s%s\n",substr($0,7,index($0,"processor")-7),substr($0,index($0,"at "))
}'
fi

if [ "x$THISOS" = "xFreeBSD" ]; then
${AWK} '
/^[A-Z]/&&/MHz/{
  if($0 !~ /^CPU/){
    printf "CPU: "
  };
  print
}
/^real memory/{
  printf "Memory size: %s\n",substr($0,index($0,"=")+2)
}
' /var/run/dmesg.boot
fi

## 
## Memory:
##     prtconf | grep Memory
## 

## SunOS:
if [ "x$THISOS" = "xSunOS" ]; then 
${PRTCONF} | grep Memory
fi

## OSF1:
if [ "x$THISOS" = "xOSF1" ]; then 
${UERF} | \
${AWK} '/physical memory/{printf "Memory size: %s\n",substr($0,index($0,"=")+2);exit}'
fi


## 
## To get network devices:
##     ls /devices/pci@*/network* | ${AWK} -F\: '{print $NF}' | sort
## 

${IFCONFIG} -a | ${AWK} '
/^[a-z]/&&!/^lo/&&/UP/{
  this_if=substr($1,1,index($1,":")-1);
  if (this_if in these_ifs)
    {}
  else{
    these_ifs[this_if];
    printf "Network(UP): %s\n",this_if
  }
}'
