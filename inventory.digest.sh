#!/bin/sh

# Section Headers in the data file are:
#	TARGET
#	HOSTNAME
#	UNAME
#	VMSTAT
#	PSRINFO
#	LOCALDISKS
#	DISKSPACE-LOCAL
# Data collected with:
#    for i in `cat mail.machines`; do echo "TARGET"; echo $i; echo "HOSTNAME"; 
#    rsh $i "hostname; echo UNAME; uname -a; echo VMSTAT; vmstat -P|grep ^Total; 
#    echo PSRINFO; if [ -f /usr/sbin/psrinfo ]; then /usr/sbin/psrinfo -v; 
#    else if [ -f /sbin/psrinfo ]; then /sbin/psrinfo -v; fi; fi; echo LOCALDISKS;
#    egrep -v '^/proc|nfs' /etc/fstab; echo DISKSPACE-LOCAL; df | 
#    egrep -v '^/proc|mailnac|netapp'"; done > mail.machines.somefile
# 

MYDATAFILE="/home/bmsnook/data/mail.machines.lastinventory"

awk '
$1 ~ /TARGET|HOSTNAME|UNAME|VMSTAT|PSRINFO|LOCALDISKS|DISKSPACE-LOCAL/ {
  ValidSection = $1
  print "ValidSection: "$ValidSection"\t"
  next
}
#$1 != ValidSection {
#  print "not section header:\t"$0
#}'
$1 ~ /TARGET|HOSTNAME/ { printf $1":" }
$1 ~ /^UNAME/ { printf $4":" }'
#'
