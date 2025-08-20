import pathlib
import argparse
import os
import sys
import yaml
import json

DEFAULT_OUTPUT_FORMAT   = "json"        ## set to "yaml" or "json"

## Accept arguments to override default behavior
parser = argparse.ArgumentParser(description="Convert file contents between YAML and JSON formats")
parser.add_argument("-p", "--project", action="append", type=str, help="project repo(s) to check (flag/arg can be repeated)")
parser.add_argument("-t", "--tokenpath", type=str, help="path to gitlab token file (default: ~/.gittoken; overrides env CI_JOB_TOKEN if set)")
parser.add_argument("--infile", type=str, help="file to read from")
parser.add_argument("--outfile", type=str, help="file to save to")
parser.add_argument("-f", "--format", type=str, help="format to use for plan display (yaml or json)")
parser.add_argument("-d", "--debug", action="store_true", help="enable debug output")
parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
# parser.add_argument("action", type=str, choices=['plan', 'validate', 'apply'], help="Action to perform (plan or apply)")
## Read arguments from command line
args = parser.parse_args()

## 
## FUNCTIONS
## 
def expand_file_path(filepath):
    try:
        abs_filepath = os.path.abspath(pathlib.Path(filepath).expanduser())
    except:
        print(f"ERROR: plan file path could not be resolved")
        return 3
    else:
        return abs_filepath
    
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
                yaml.dump(parsed_file_contents, file)
            else:
                if args.debug: print(f"DEBUG: exporting json to file")
                json.dump(parsed_file_contents, file)
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
                if args.debug: print(f"read yaml", file=sys.stderr)
                data = yaml.safe_load(file)
                return data
            elif fext in ["json"]:
                if args.debug: print(f"read json", file=sys.stderr)
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

def print_plan_file():
    if output_format == "yaml":
        if args.debug: print(f"DEBUG: exporting yaml to console", file=sys.stderr)
        print(yaml.dump(parsed_file_contents))
    else:
        if args.debug: print(f"DEBUG: exporting json to console", file=sys.stderr)
        print(json.dumps(parsed_file_contents, indent=2))


## 
## MAIN
## 

## Set output format (yaml or json)
## 
output_format = DEFAULT_OUTPUT_FORMAT
if args.format:
    if args.debug: print(f"DEBUG: args.format = %r" % (args.format))
    if args.format.lower() in ["yaml", "json"]:
        output_format = args.format.lower()
    else:
        print(f"Specified output format %r not recognized: use 'yaml' or 'json'" % args.format.lower())
        sys.exit(2)

if args.infile:
    input_file = expand_file_path(args.infile)
    parsed_file_contents = read_plan_file(input_file)
else:
    print("ERROR: no input file provided")
    sys.exit(1)

if args.outfile:
    output_file = expand_file_path(args.outfile)
    save_plan_file(output_file)
else:
    # print(json.dumps(parsed_file_contents, indent=2))
    print_plan_file()