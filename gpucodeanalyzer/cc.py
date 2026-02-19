#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
import shlex
import sys
from pathlib import Path

def get_compiler():
    compiler = shutil.which(os.getenv('CC', 'cc'))
    return compiler

def get_flags():
    return ["-Wmaybe-uninitialized"]

def get_include_dirs():
    return [Path(__file__).parent / '..' / 'src',
            Path(__file__).parent / 'isa' / 'sass',
            ]

def get_lib_dirs():
    return []

def get_libs():
    return []

def get_objects():
    return [Path(__file__).parent / '..' / 'src' / 'pathtrace.o']

def main():
    p = argparse.ArgumentParser(description="Run compiler on gca-cfg2c code")

    p.add_argument("args", nargs="+", help="Source files and other arguments to CC")
    p.add_argument("-o", dest="output")
    p.add_argument("-g", dest="debug", action="store_true")

    args = p.parse_args()

    cmd = [get_compiler()]

    if not any([x.startswith("-O") for x in args.args]):
        cmd.append("-O1") # needed for warnings for gcc

    cmd.extend(get_flags())
    if args.output:
        cmd.extend(['-o', args.output])
    if args.debug:
        cmd.append('-g')

    cmd.extend([f"-I{dir}" for dir in get_include_dirs()])
    cmd.extend([f"-L{dir}" for dir in get_lib_dirs()])
    cmd.extend(args.args)
    cmd.extend([f"-l{dir}" for dir in get_libs()])
    cmd.extend([str(s) for s in get_objects()])

    print(shlex.join(cmd), file=sys.stderr)
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
