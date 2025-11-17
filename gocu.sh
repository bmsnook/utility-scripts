#!/bin/sh

gocu() {
    local chrome_args=()
    local urls_to_open=()
    local existing_window
    local new_window
    local incognito
    local url_prefix
    local gitify_url
    local git_include_cwd
    local test_only
    local verbose
    local OPTIND OPTARG
    while getopts ":egGhinp:tv" opt; do
        case $opt in
            e)
                existing_window=1
                ;;
            h)
                echo "gocu: a simple tool to open URLs in Google Chrome"
                echo "  gocu = \"go chrome url\" or \"go open chrome url\""
                echo ""
                echo "Usage: gocu [options] [urls]"
                echo ""
                echo "Options:"
                echo "  -e    Use an existing Chrome window"
                echo "  -n    Use a new Chrome window"
                echo "  -i    Use incognito mode"
                echo "  -g    Prefix path(s) with current git repo URL"
                echo "  -G    Prefix path(s) with current git repo URL+cwd"
                echo "  -p PREFIX   Specify a prefix URL for other sites(overridden by -g or -G)"
                echo "  -t    Test only (does not open Chrome; implies -v)"
                echo "  -v    Verbose (prints URLs to open, each on a new line)"
                echo ""
                echo "Examples:"
                echo "  gocu https://www.udemy.com/"
                echo "  gocu apple.com bing.com www.comcast.com"
                echo "  gocu -i citibank.com"
                echo "  gocu -p aws.amazon.com getting-started/hands-on prescriptive-guidance"
                echo "NOTE: -g and -G _must_ be used from within a git repo"
                echo "  Both require relative paths and attempt to resolve branch and remote"
                echo "    -g path relative from the repo root but cwd can be any directory"
                echo "    -G path relative from the cwd"
                echo '  gocu -g $(cat /tmp/findresults.txt)'
                echo '  gocu -G $(find . name 'main.tf')'
                return 0
                ;;
            i)
                incognito=1
                ;;
            n)
                new_window=1
                ;;
            g)
                gitify_url=1
                ;;
            G)
                gitify_url=1
                git_include_cwd=1
                ;;
            p)
                url_prefix=$OPTARG
                ;;
            t)
                test_only=1
                ;;
            v)
                verbose=1
                ;;
            *)
                ;;
        esac
    done
    shift $((OPTIND - 1))
    ## set default chrome args (i.e., --new-window or empty to use existing window)
    if [ ! -n "$existing_window" ]; then  
        ## if neither existing or new window is specified, default to new window
        chrome_args+=("--new-window")
    fi
    if [ -n "$new_window" ]; then
        if [[ ! "${chrome_args[@]}" =~ "--new-window" ]]; then
            chrome_args+=("--new-window")
        fi
    fi
    if [ -n "$incognito" ]; then
        chrome_args+=("--incognito")
    fi
    if [[ -n "$url_prefix" || -n "$gitify_url" ]]; then
        # gitify overrides regular prefix option if both are set
        if [[ -n "$gitify_url" ]]; then
            git_default_branch_name=$(git config --get init.defaultBranch)
            git_branch_name=$(git branch --show-current)
            ## remote origin can be retrieved from the git config in multiple ways
            ##   git remote get-url origin
            ##   git config remote.origin.url
            if [[ -n "$git_branch_name" ]]; then
                url_prefix=$(git remote get-url origin | awk '
                    /^git@/{gsub("git@","");sub(":","/")}
                    /\.git$/{gsub("\.git$","")}
                    !/^https/{$0="https://"$0}
                    {print}')
                ## if the branch exists on the remote, use the branch name, 
                ## otherwise use the default branch name
                if [[ $(git ls-remote --exit-code --heads origin ${git_branch_name}) ]]; then
                    url_prefix+="/blob/${git_branch_name}"
                else
                    echo "WARNING: Branch \"${git_branch_name}\" does not exist on remote; using default branch \"${git_default_branch_name}\"" >&2
                    url_prefix+="/blob/${git_default_branch_name}"
                fi
            else
                echo "ERROR: Not a git repository; run from within a git repo" && return 1
            fi
            if [[ -n "$git_include_cwd" ]]; then
                git_relative_path=$(git rev-parse --show-prefix)
                if [[ -n "$git_relative_path" ]]; then
                    url_prefix+="/${git_relative_path}"
                fi
            fi
        fi
        urls_to_open=($(printf "${url_prefix%/}/%s "  ${@#/}))
    else
        urls_to_open=($(printf "%s " $@))
    fi
    if [[ -n "$verbose" || -n "$test_only" ]]; then
        # echo "Opening URLs: ${urls_to_open}"
        printf "%s\n" "${urls_to_open[@]}"
    fi
    if [[ ! -n "$test_only" ]]; then
        open -na "Google Chrome" --args "${chrome_args[@]}" ${urls_to_open[@]}
    fi
    return 0
}
