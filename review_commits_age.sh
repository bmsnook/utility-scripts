#!/bin/sh

EPOCH_TIME_CURRENT=$(date +"%s")
if date -v-1d > /dev/null 2>&1; then
  # BSD/macOS
  EPOCH_SECONDS_6_MONTHS_AGO=$(date -u -j -v -6m "+%s")
else
  # GNU
  EPOCH_SECONDS_6_MONTHS_AGO=$(date -u -d '6 months ago' "+%s")
fi 
REPOS=(gcp-terraform)
for EACH_REPO in ${REPOS[@]}; do 
    cat /dev/null > "${EACH_REPO}.branches-to-remove.txt"
    cat /dev/null > "${EACH_REPO}.branches-to-remove-commands.txt"
    BRANCHES_TO_REMOVE_FILE=$(readlink -fn "${EACH_REPO}.branches-to-remove.txt")
    BRANCHES_TO_REMOVE_CMDS_FILE=$(readlink -fn "${EACH_REPO}.branches-to-remove-commands.txt")
    BRANCH_LOG_FILE="${EACH_REPO}.branches.$(date "+%Y%m%d_%H%M").log.txt"
    git clone git@gitlab.com:fetcherr/devops/${EACH_REPO}.git
    cd ${EACH_REPO}
    # git branch -r
    git fetch --all
    git branch -r | grep -v '\->' | sed "s,\x1B\[[0-9;]*[a-zA-Z],,g" | while read remote; do git branch --track "${remote#origin/}" "$remote"; done
    git pull --all
    git checkout master
    for EACH_BRANCH in $(git branch | awk '$NF!="master"'); do
        BRANCH_EPOCH_LAST_UPDATE=$(git log --date=raw --name-status -1 ${EACH_BRANCH} | awk '/^Date:/{print $2}')
        if [[ ${BRANCH_EPOCH_LAST_UPDATE} -lt ${EPOCH_SECONDS_6_MONTHS_AGO} ]]; then
            echo "Branch \"${EACH_BRANCH}\" is OLD"
            git log --name-status -1 "${EACH_BRANCH}" | egrep '^Date:'
            echo ${EACH_BRANCH} >> ${BRANCHES_TO_REMOVE_FILE}
            echo "git branch -D ${EACH_BRANCH}" >> ${BRANCHES_TO_REMOVE_CMDS_FILE}
        else
            : # echo "Branch \"${EACH_BRANCH}\" is NEW"
        fi
    done
    cd -
done
