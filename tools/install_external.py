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
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
PIP_REQUIRES = os.path.join(ROOT, 'tools', 'pip-requires')
PIP_REQUIRES_TEST = os.path.join(ROOT, 'tools', 'pip-requires-test')


def die(message, *args):
    print >> sys.stderr, message % args
    sys.exit(1)


def run_command(cmd, redirect_output=True, check_exit_code=True, shell=False):
    """
    Runs a command in an out-of-process shell, returning the
    output of that command.  Working directory is ROOT.
    """
    if redirect_output:
        stdout = subprocess.PIPE
    else:
        stdout = None

    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=stdout, shell=shell)
    output = proc.communicate()[0]
    if check_exit_code and proc.returncode != 0:
        die('Command "%s" failed.\n%s', ' '.join(cmd), output)
    return output


HAS_WGET = bool(run_command(['which', 'wget'], check_exit_code=False).strip())


def configure_git():
    """
    Configure git to add git hooks
    """
    print "Configure git"
    run_command("%s/tools/configure_git.sh" % ROOT, shell=True)


def install_pip():
    """
    Install pip to tools/externals
    """
    print "Installing pip via wget"
    if not HAS_WGET:
        die("ERROR: wget not found, please install.")

    tempdir = tempfile.mkdtemp()
    run_command(['wget', '-O', os.path.join(tempdir, 'get-pip.py'), 'https://bootstrap.pypa.io/get-pip.py'])
    run_command("python %s/get-pip.py --prefix=%s --ignore-installed" % (tempdir, os.path.join(ROOT, 'tools/externals')), shell=True)
    shutil.rmtree(tempdir)


def install_dependencies():
    """
    Install external dependencies
    """
    lib_dir = os.path.join(ROOT, "tools/externals/lib/")
    for pathname in os.listdir(lib_dir):
        if pathname.startswith('python'):
            lib_path = os.path.join(lib_dir, pathname)
            link_path = os.path.join(lib_dir, "python")
            if not os.path.exists(link_path):
                os.symlink(lib_path, link_path)
            elif not os.path.exists(os.readlink(link_path)):
                os.remove(link_path)
                os.symlink(lib_path, link_path)
    envExport = "export PYTHONPATH=$PYTHONPATH:%s/tools/externals/lib/python/site-packages" % ROOT
    # run_command("%s;%s/tools/externals/usr/bin/pip install -r %s -t %s/externals/" % (envExport, ROOT, PIP_REQUIRES, ROOT), shell=True)
    run_command("%s;python %s/tools/externals/bin/pip install -r %s --prefix=%s/tools/externals/" % (envExport, ROOT, PIP_REQUIRES_TEST, ROOT), shell=True)


def print_help():
    help = """
Pilot development environment setup is complete.

To enable pilot dev environment by running:

$ source tools/setup_dev.sh
"""
    print help


def main():
    configure_git()

    print "Installing pip via wget"
    install_pip()

    print "Installing dependencies via pip"
    install_dependencies()
    print_help()

if __name__ == "__main__":
    main()
