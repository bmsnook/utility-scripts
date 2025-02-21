#!/bin/sh

VERBOSE="false"
if [[ $1 == "-v" ]]; then
    VERBOSE="true"
    shift
fi
if [[ $# -gt 0 ]]; then
    REPOS=$@
else
    REPOS=(gcp-terraform)
fi

EPOCH_TIME_CURRENT=$(date +"%s")
if date -v-1d > /dev/null 2>&1; then
  # BSD/macOS
  EPOCH_SECONDS_6_MONTHS_AGO=$(date -u -j -v -6m "+%s")
else
  # GNU
  EPOCH_SECONDS_6_MONTHS_AGO=$(date -u -d '6 months ago' "+%s")
fi 

for EACH_REPO in ${REPOS[@]}; do 
    cat /dev/null > "${EACH_REPO}.branches-to-remove.txt"
    cat /dev/null > "${EACH_REPO}.branches-to-remove-commands.txt"
    BRANCHES_TO_REMOVE_FILE=$(readlink -fn "${EACH_REPO}.branches-to-remove.txt")
    BRANCHES_TO_REMOVE_CMDS_FILE=$(readlink -fn "${EACH_REPO}.branches-to-remove-commands.txt")
    BRANCH_LOG_FILE="${EACH_REPO}.branches.$(date "+%Y%m%d_%H%M").log.txt"

    if [[ ! -d ${EACH_REPO} ]]; then 
        if [[ ${VERBOSE} == "true" ]]; then
            git clone git@gitlab.com:fetcherr/devops/${EACH_REPO}.git
        else    
            git clone git@gitlab.com:fetcherr/devops/${EACH_REPO}.git > /dev/null 2>&1
        fi
    fi
    if [[ -d ${EACH_REPO} ]]; then 
        cd ${EACH_REPO}
        # git branch -r
        if [[ ${VERBOSE} == "true" ]]; then
            git fetch --all
            git branch -r | grep -v '\->' | sed "s,\x1B\[[0-9;]*[a-zA-Z],,g" | \
                while read remote; do 
                    git branch --track "${remote#origin/}" "$remote"; 
                done
            git pull --all
            git checkout master
        else
            git fetch --all > /dev/null 2>&1
            git branch -r | grep -v '\->' | sed "s,\x1B\[[0-9;]*[a-zA-Z],,g" | \
                while read remote; do 
                    git branch --track "${remote#origin/}" "$remote"; 
                done > /dev/null 2>&1
            git pull --all > /dev/null 2>&1
            git checkout master > /dev/null 2>&1
        fi
        for EACH_BRANCH in $(git branch | awk '$NF!="master"'); do
            BRANCH_EPOCH_LAST_UPDATE=$(git log --date=raw --name-status -1 ${EACH_BRANCH} | awk '/^Date:/{print $2}')
            if [[ ${BRANCH_EPOCH_LAST_UPDATE} -lt ${EPOCH_SECONDS_6_MONTHS_AGO} ]]; then
                # echo "INFO: Branch \"${EACH_BRANCH}\" is OLD"
                echo "## OLD BRANCH: ${EACH_BRANCH}" >> ${BRANCHES_TO_REMOVE_FILE}
                git log --name-status -1 "${EACH_BRANCH}" | egrep '^Date:' >> ${BRANCHES_TO_REMOVE_FILE}
                echo "git branch -D ${EACH_BRANCH}" >> ${BRANCHES_TO_REMOVE_CMDS_FILE}
            else
                : # echo "INFO: Branch \"${EACH_BRANCH}\" is NEW"
            fi
        done
        cd -
    else
        echo "ERROR: Could not clone/use repo \"${EACH_REPO}\""
    fi
done

echo "Review last commit of branches last updated more than 6 months ago:"
ls -l *branches-to-remove.txt
echo ""
echo "Remove branches using \"source COMMAND-FILE\": "
ls -l *branches-to-remove-commands.txt
