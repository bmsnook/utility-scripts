#!/bin/sh

LOGDIR="/tmp/audit.userfiles.`uname -n`"

AWK= 
[ -f /usr/local/bin/awk ] && AWK=/usr/local/bin/awk  && ls -il ${AWK}
[ -f /usr/bin/awk ] && AWK=/usr/bin/awk  && ls -il ${AWK}
[ -f /bin/awk ] && AWK=/bin/awk  && ls -il ${AWK}
[ -f /usr/local/bin/nawk ] && AWK=/usr/local/bin/nawk  && ls -il ${AWK}
[ -f /usr/bin/nawk ] && AWK=/usr/bin/nawk  && ls -il ${AWK}
[ -f /bin/nawk ] && AWK=/bin/nawk  && ls -il ${AWK}
[ -f /usr/local/bin/gawk ] && AWK=/usr/local/bin/gawk  && ls -il ${AWK}
[ -f /usr/bin/gawk ] && AWK=/usr/bin/gawk  && ls -il ${AWK}
[ -f /bin/gawk ] && AWK=/bin/gawk  && ls -il ${AWK}
export AWK
#echo "AWK=${AWK}"

mkdir ${LOGDIR} && cd ${LOGDIR}

${AWK} -F: '{
  uid[$1]=$3
}
END{
  for(user in uid){
    cmd=sprintf("find / /ms /var -mount -user %s -ls >> audit.files.uid_%s_%s.txt",uid[user],uid[user],user)
    printf "%s\n",cmd
    system(cmd)
  }
}' /etc/passwd
