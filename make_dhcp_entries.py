#!/usr/bin/env python3

import sys

## 
## INPUT: A file containing data formatted like this:
## 
## A1:B2:C3:D4:E5:F6   192.168.0.254    Amazon Echo Spot Kitchen
## 

## OUTPUT: 
## host amazon-echo-spot-kitchen {
##     hardware ethernet a1:b2:c3:d4:e5:f6;
##     fixed-address 192.168.0.254;
##     ddns-hostname amazon-echo-spot-kitchen;
## }
## 


def process_file(DFILE):
    with open(DFILE, 'r') as f:
        for line in f:
            l = line.split()
            mac, ip, name = l[0].lower(), l[1], '-'.join(l[2:]).lower()
            stanza = """host %s {
    hardware ethernet %s;
    fixed-address %s;
    ddns-hostname %s;
}
""" % (name, mac, ip, name)
            print(stanza)
    f.close()

process_file(sys.argv[1])

