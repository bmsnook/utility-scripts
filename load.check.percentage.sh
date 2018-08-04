#!/bin/sh

swap -s | nawk '{gsub("k","");print; printf "%s / %s == %s%%\n",$(NF-3),$(NF-3)+$(NF-1),$(NF-3)/($(NF-3)+$(NF-1))*100}'
