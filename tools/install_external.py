#!/usr/bin/env python
# Copyright European Organization for Nuclear Research (CERN)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0OA
#
# Authors:
# - Wen Guan, <wen.guan@cern.ch>, 2016


import os
import subprocess
import sys
import imp

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
PIP_REQUIRES = os.path.join(ROOT, 'tools', 'pip-requires')
PIP_REQUIRES_TEST = os.path.join(ROOT, 'tools', 'pip-requires-test')
EXTERNALS = os.path.join(ROOT, 'tools', 'externals')


def die(message, *args):
    print >> sys.stderr, message % args
    sys.exit(1)


def run_command(cmd, redirect_output=True, check_exit_code=True, shell=False):
    """
    Runs a command in an out-of-process shell, returning the
    output of that command.  Working directory is ROOT.
    """
    if shell:
        cmd = ['sh', '-c', cmd]
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE if redirect_output else None)
    output = proc.communicate()[0]
    if check_exit_code and proc.returncode != 0:
        # print("ec = %d " % proc.returncode)
        die('Command "%s" failed.\n%s', ' '.join(cmd), output)
    return output


def has_module(mod):
    try:
        imp.find_module(mod)
        return True
    except ImportError:
        return False


def configure_git():
    """
    Configure git to add git hooks
    """
    print "Configure git"
    run_command(['sh', "./tools/configure_git.sh"])


def install_dependencies():
    """
    Install external dependencies
    """
    lib_dir = os.path.join(EXTERNALS, "lib")
    if os.path.exists(lib_dir):
        for pathname in os.listdir(lib_dir):
            if pathname.startswith('python'):
                lib_path = os.path.join(lib_dir, pathname)
                link_path = os.path.join(lib_dir, "python")
                if not os.path.exists(link_path):
                    os.symlink(lib_path, link_path)
                elif not os.path.exists(os.readlink(link_path)):
                    os.remove(link_path)
                    os.symlink(lib_path, link_path)
    else:
        os.makedirs(lib_dir)

    python_path = os.path.abspath(os.path.join(lib_dir, 'python', 'site-packages'))
    if "PYTHONPATH" in os.environ:
        python_path = python_path + ":" + os.environ["PYTHONPATH"]
    os.environ["PYTHONPATH"] = python_path
    if "LD_LIBRARY_PATH" in os.environ:
        os.environ["LD_LIBRARY_PATH"] = lib_dir + ":" + os.environ["LD_LIBRARY_PATH"]

    run_command([sys.executable, os.path.join(ROOT, "tools/install_deps.py"), '--no_setup', '--prefix', EXTERNALS],
                redirect_output=False)


def print_help():
    help = """
Pilot development environment setup is complete.

To enable pilot dev environment by running:

$ source tools/setup_dev.sh
"""
    print help


def main():
    cwd = os.getcwd()
    print os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # configure_git() # it is already configured, I suppose

    print "Installing dependencies via pip"
    install_dependencies()

    print_help()
    os.chdir(cwd)

if __name__ == "__main__":
    main()
