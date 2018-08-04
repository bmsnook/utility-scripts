#!/bin/sh

if [ $# -gt 0 ]; then
  for net in $*; do
    echo "INFO: testing network ${net}"
    octet=2
    while [ $octet -le 254 ]; do
      ping ${net}.${octet}
      octet=`echo $octet + 1 | bc`
      sleep 1
    done
    sleep 2
  done
else
  echo "Usage:  $0 [NETWORK]"
  echo "    e.g.:"
  echo "        $0 127.0.0"
fi

