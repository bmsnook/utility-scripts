#!/bin/sh

nawk -F: '
BEGIN{
  OFS=":"
  while(getline<"/etc/shadow.historical.pre-dpkg"){
#    printf "DEBUG: key: %-16s   value: %-16s (len=%s)\n",$1,$2,length($2)
    if($1!="root" && length($2)>10){
      shadow[$1]=$2
    }
  }
}
{
#  print $1
  if (shadow[$1]){
    $2=shadow[$1]
    print
  }else{
    print
  }
}
END{
#  print "END RESULTS:"
#  for (each in shadow){
#    printf "%s: %s\n",each,shadow[each]
#  }
}' /etc/shadow 
