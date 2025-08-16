#!/Users/bmsnook/github/shared-scratch/.venv/bin/python

## pip install python-gitlab
##   https://python-gitlab.readthedocs.io/en/stable/
import gitlab
import pathlib
import argparse
import os
import sys
import yaml
import json
## custom module to process various datetime string formats and compare values
import date_compare

## 
## GLOBAL VARIABLES - intended to be static defaults
## 
## Specify path to a PAT (environment variable CI_JOB_TOKEN overrides if set)
PRIVATE_TOKEN_FILE  = "~/.gittoken"
PROTECTED_BRANCHES  = ["master", "main"]
DEFAULT_COMMIT_AGE_MONTHS_THRESHOLD = 3
DEFAULT_OUTPUT_FORMAT   = "yaml"        ## set to "yaml" or "json"

## Defaults for Python Gitlab API Module
##   CHANGE to appropriate values for your environment
GITLAB_BASE_URL     = r"https://gitlab.com"
DEFAULT_GL_NAMESPACE    = "mycompany"
DEFAULT_GL_GROUP_ID     = 11112222
DEFAULT_GL_GROUP_NAME   = "devops"
DEFAULT_GL_GROUP_PATH   = "mycompany/devops"
DEFAULT_GL_PROJECTS     = {
    "apps": 11110000,
    "devops": 11112222,
    "aws-terraform": 22223333,
    "gcp-terraform": 33334444,
    "helm-charts": 44445555
    }

## 
## GLOBALS - Dynamic
## 
all_projects = set()
projects_expire_plan = {}
plan_branches_not_found = {}
plan_branches_not_deleted = {}
output_format = DEFAULT_OUTPUT_FORMAT
plan_filename = None


## Accept arguments to override default behavior
parser = argparse.ArgumentParser(description="Expire branches with old last commits (default 3 months) in projects (defaults: apps, gcp-terraform)")
parser.add_argument("-p", "--project", action="append", type=str, help="project repo(s) to check (flag/arg can be repeated)")
parser.add_argument("-m", "--months", type=int, help="number of months for expiration (default: 3)")
parser.add_argument("-t", "--tokenpath", type=str, help="path to gitlab token file (default: ~/.gittoken; overrides env CI_JOB_TOKEN if set)")
parser.add_argument("--infile", type=str, help="plan file to read from")
parser.add_argument("--outfile", type=str, help="plan file to save to")
parser.add_argument("-f", "--format", type=str, help="format to use for plan display (yaml or json)")
parser.add_argument("-d", "--debug", action="store_true", help="enable debug output")
parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
parser.add_argument("action", type=str, choices=['plan', 'validate', 'apply'], help="Action to perform (plan or apply)")
## Read arguments from command line
args = parser.parse_args()


## 
## FUNCTIONS
## 
def get_token(filepath):
    try:
        abs_filepath = pathlib.Path(filepath).expanduser()
        with open(abs_filepath, 'r') as file:
            token_content = file.read().strip()
    except:
        return False
    else:
        return token_content

def expand_file_path(filepath):
    try:
        abs_filepath = os.path.abspath(pathlib.Path(filepath).expanduser())
    except:
        print(f"ERROR: plan file path could not be resolved")
        return 3
    else:
        return abs_filepath

def get_group_id(target_group):
    try:
        tg = int(target_group)
    except:
        t_parts = target_group.split("/")
        if t_parts[-1] == "":
            del t_parts[-1]
        if len(t_parts) < 2:
            tg = DEFAULT_GL_NAMESPACE + "/" + target_group
        else:
            tg = target_group
    else:
        pass

    try:
        # print(f"DEBUG: g = gl.groups.get(%r)" % (tg))
        g = gl.groups.get(tg)
    except:
            print(f"ERROR: could not find group %r => %r" % (target_group, tg))
            # sys.exit(1)
            return 1
    else:
        # print(f"DEBUG: return: %r => %r" % (g.id, g.full_path))
        return g.id
    
def get_project_id(target_project):
    try:
        tp = int(target_project)
    except:
        ## split path parts while removing any trailing slash
        t_parts = target_project.strip("/").split("/")
        if len(t_parts) < 2:
            tp = DEFAULT_GL_GROUP_PATH + "/" + target_project
        elif len(t_parts) < 3:
            tp = DEFAULT_GL_NAMESPACE + "/" + target_project
        else:
            # pass
            tp = target_project.strip("/")

    try:
        if args.debug: print(f"DEBUG: p = gl.projects.get(%r)" % (tp))
        p = gl.projects.get(tp)
    except:
        print(f"ERROR: could not find project %r => %r" % (target_project, tp))
        return 1    
    else:
        if args.debug: print(f"DEBUG: return: %r => %r" % (p.id, p.path_with_namespace))
        return p.id

def get_project_path(target_project):
    try:
        tp = int(target_project)
    except:
        ## split path parts while removing any trailing slash
        t_parts = target_project.strip("/").split("/")
        if len(t_parts) < 2:
            tp = DEFAULT_GL_GROUP_PATH + "/" + target_project
        elif len(t_parts) < 3:
            tp = DEFAULT_GL_NAMESPACE + "/" + target_project
        else:
            # pass
            tp = target_project.strip("/")

    try:
        if args.debug: print(f"DEBUG: p = gl.projects.get(%r)" % (tp))
        p = gl.projects.get(tp)
    except:
        print(f"ERROR: could not find project %r => %r" % (target_project, tp))
        return 1    
    else:
        if args.debug: print(f"DEBUG: return: %r => %r" % (p.id, p.path_with_namespace))
        return p.path_with_namespace
    
def register_branch_to_expire(exp_project, exp_branch, exp_date):
    global projects_expire_plan
    target_project = projects_expire_plan.get(exp_project)
    # if exp_project in projects_expire_plan:
    if target_project is not None:
        # print(f"DEBUG: found {exp_project}")
        if exp_branch in target_project:
            # print(f"\tDEBUG: found branch %r" % exp_branch)
            projects_expire_plan[exp_project].update({exp_branch: exp_date})
        else:
            # print(f"\tDEBUG: did NOT find branch %r" % exp_branch)
            projects_expire_plan[exp_project][exp_branch] = exp_date
    else:
        # print(f"DEBUG: NOTFOUND: {exp_project}")
        projects_expire_plan[exp_project] = {exp_branch: exp_date}

def find_stale_branches(input_projects):
    global gl
    for each_project in input_projects:
        if args.debug: print(f"DEBUG: query_project = %r" % (each_project))
        query_project = gl.projects.get(each_project)
        all_query_project_branches = query_project.branches.list(iterator=True)
        for each_query_project_branch in all_query_project_branches:
            current_branch_name = each_query_project_branch.attributes['name']
            project_protected_branches = query_project.protectedbranches.list()
            if current_branch_name in PROTECTED_BRANCHES or current_branch_name in project_protected_branches:
                # print(f"DEBUG: IGNORING %r" % (current_branch_name))
                pass
            else:
                if args.debug: print(f"DEBUG: PROCESSING branch %r" % (current_branch_name))
                ## NOTE: modifying "(ref_name=current_branch_name" to add ", iterator=True" before ")"
                ## changes the returned datatype from a list to a RESTAPI object, which breaks the 
                ## later subscript reference "[0]" to get the first (latest) commit; a pagination error 
                ## will be produced if more than 20 commits are returned, but can be safely ignored 
                ## because only the first returned commit is needed
                all_current_branch_commits = query_project.commits.list(ref_name=current_branch_name, get_all=False)
                if args.debug: print(f"DEBUG-DEBUG-DEBUG: printing 'all_current_branch_commits'")
                latest_branch_commit = all_current_branch_commits[0]
                if args.debug: print(f"DEBUG3: print latest: %r" % (latest_branch_commit))
                if args.debug: print(f"DEBUG4: LAST COMMIT DATE: %r" % (latest_branch_commit.committed_date))
                # if date_compare.date_more_than_one_month_ago(latest_branch_commit.committed_date):
                if date_compare.date_more_than_x_months_ago(latest_branch_commit.committed_date,commit_age_months_threshold):
                    if args.verbose: print(f"INFO: expiring %r branch %r last updated %r" % (
                        query_project.path_with_namespace, 
                        current_branch_name, 
                        latest_branch_commit.committed_date))
                    register_branch_to_expire(
                        query_project.path_with_namespace, 
                        current_branch_name, 
                        latest_branch_commit.committed_date)

def print_branches_to_expire(out_fmt=output_format):
    global projects_expire_plan
    if out_fmt == "yaml":
        print(yaml.dump(projects_expire_plan))
    else:
        print(json.dumps(projects_expire_plan, indent=2))

def save_plan_file(fname):
    if fname is None:
        print(f"Error: specify a file to save to with \"--outfile\" flag")
        return 6
    else:
        fext = fname.lower().split(".")[-1]
        if fext in ["yaml", "yml"]:
            format = "yaml"
        elif fext in ["json"]:
            format = "json"
        else:
            format = output_format

    try:
        with open(fname, "w") as file:
            if format == "yaml":
                if args.debug: print(f"DEBUG: exporting yaml to file")
                yaml.dump(projects_expire_plan, file)
            else:
                if args.debug: print(f"DEBUG: exporting json to file")
                json.dump(projects_expire_plan, file)
    except PermissionError:
        print(f"Error: Permission denied to write to '{fname}'")
    except IOError as e:
        print(f"IOError: An error occurred while writing to the file: {e}")
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")

def read_plan_file(fname):
    fext = fname.lower().split(".")[-1]
    try:
        with open(fname, 'r') as file:
            if fext in ["yaml", "yml"]:
                print(f"read yaml")
                data = yaml.safe_load(file)
                return data
            elif fext in ["json"]:
                print(f"read json")
                data = json.load(file)
                return data
            else:
                print(f"ERROR: could not determine file type")
                return 5
    except FileNotFoundError:
        print(f"Error: File not found: {fname}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in: {fname}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    
def delete_branches():
    global projects_expire_plan
    for project_name in projects_expire_plan:
        print(f"INFO: processing project %r" % (project_name))
        current_project = gl.projects.get(project_name)
        project_branches = projects_expire_plan.get(project_name)
        for branch_name in project_branches:
            try:
                branch_instance = current_project.branches.get(branch_name)
            except:
                print(f"WARNING: could not retrieve project %r branch %r" % (project_name, branch_name))
            else:
                print(f"INFO: marked for deletion: project %r branch %r\n\tlast update:\t%s\t%r\n\t%s" % (
                    project_name, 
                    branch_name, 
                    branch_instance.commit['committed_date'], 
                    branch_instance.commit['title'],
                    branch_instance.commit['web_url']
                ))
                if args.action == "apply":
                    # print(f"DEMO: DELETE STAND-IN")
                    try:
                        current_project.branches.delete(branch_name)
                    except gitlab.exceptions.GitlabDeleteError as e:
                        print(f"ERROR: unable to delete project %r branch %r: %s" % (project_name, branch_name, e))
                        print(f"ERROR: verify token/key has correct API write permissions")
                    except Exception as e:
                        print("ERROR: error removing project %r branch %r - %s" % (project_name, branch_name, e))
                    else:
                        try:
                            deleted_branch = current_project.branches.get(branch_name)
                        except gitlab.exceptions.GitlabGetError as e:
                            ## indicates 404: 404 Branch Not Found
                            print(f"INFO: deletion SUCCESSFUL: project %r branch %r removed" % (project_name, branch_name))
                        except gitlab.exceptions.GitlabHttpError as e:
                            print(f"INFO: project %r branch %r could not be retrieved: %s" %(project_name, branch_name, e))
                        else:
                            print(f"WARNING: project %r branch %r NOT removed" % (project_name, branch_name))



## 
## MAIN
## 

## Set access token
##     In decreasing preference: 
##         CLI token file arg  >  CI_JOB_TOKEN env var  >  default token file
if args.tokenpath:
    access_token_file_path = args.tokenpath
    gitlab_access_token = get_token(access_token_file_path)
else:
    access_token_file_path = PRIVATE_TOKEN_FILE
    try:
        CI_JOB_TOKEN = os.environ["CI_JOB_TOKEN"]
    except:
        try:
            gitlab_access_token = get_token(access_token_file_path)
        except:
            print("ERROR: could not read token")
            sys.exit(1)
        else:
            # print(f"DEBUG: Found token: '{gitlab_access_token}'")
            pass
    else:
        gitlab_access_token = CI_JOB_TOKEN

    
## Set output format (yaml or json)
## 
if args.format:
    if args.debug: print(f"DEBUG: args.format = %r" % (args.format))
    if args.format.lower() in ["yaml", "json"]:
        output_format = args.format.lower()
    else:
        print(f"Specified output format %r not recognized: use 'yaml' or 'json'" % args.format.lower())
        sys.exit(2)

## Instantiate a Gitlab object
## 
gl = gitlab.Gitlab(url=GITLAB_BASE_URL, private_token=gitlab_access_token)
# gl.enable_debug()
gl.auth()


if args.infile:
    input_file = expand_file_path(args.infile)
    projects_expire_plan = read_plan_file(input_file)
else:
    ## Set projects to check for branches that should be expired/removed
    if args.project:
        if args.debug: print(f"DEBUG: found project argument(s): %r" % (args.project))
        for each_project in args.project:
            if args.debug: print(f"DEBUG: looking up project ID for %r" % each_project)
            all_projects.add(get_project_id(each_project))
    else:
        if args.debug: print(f"DEBUG: did NOT find project argument(s); checking default project list")
        for each_project in DEFAULT_GL_PROJECTS:
            if args.debug: print(f"DEBUG: looking up project ID for %r" % each_project)
            all_projects.add(get_project_id(each_project))

    if args.debug: print(f"DEBUG: current value of 'all_projects':")
    print(all_projects)

    ## Set commit age (months) to use as threshold for expiring/removing branches
    if args.months:
        commit_age_months_threshold = args.months
    else:
        commit_age_months_threshold = DEFAULT_COMMIT_AGE_MONTHS_THRESHOLD

    find_stale_branches(all_projects)

if args.outfile:
    output_file = expand_file_path(args.outfile)
    save_plan_file(output_file)


print("")

if args.action == "plan":
    if args.debug: print(f"DEBUG: plan steps")
    print_branches_to_expire(output_format)
# elif args.action == "apply":
elif args.action in ["validate", "apply"]:
    if args.debug: print(f"DEBUG: apply steps")
    print(f"INFO: Deleting branches per plan:")
    print_branches_to_expire(output_format)
    delete_branches()
else:
    print(f"ERROR: unrecognized action %r" % (args.action))
