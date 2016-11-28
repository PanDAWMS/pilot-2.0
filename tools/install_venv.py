#    copyright: European Organization for Nuclear Research (CERN)
#    @license: Licensed under the Apache License, Version 2.0 (the "License");
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at U{http://www.apache.org/licenses/LICENSE-2.0}
"""
Installation script Pilot's development virtualenv
"""

import optparse
import os
import subprocess
import sys
import imp
from distutils.spawn import find_executable
import tempfile
import shutil
# import urllib2

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
VENV = os.path.join(ROOT, '.venv')
PIP_DEPS = os.path.join(ROOT, 'tools', 'install_deps.py')


def die(message, *args):
    print >> sys.stderr, message % args
    sys.exit(1)


def download(url, to_path):
    print 'Downloading %s into %s' % (url, to_path)
    req = urlopen(url)
    with open(to_path, 'wb') as fp:
        for line in req:
            fp.write(line)
    return to_path


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


HAS_EASY_INSTALL = bool(find_executable("easy_install"))
HAS_VIRTUALENV = has_module('virtualenv')
HAS_PIP = has_module('pip')


def create_virtualenv(venv=VENV):
    """
    Creates the virtual environment and installs PIP only into the
    virtual environment
    """
    global HAS_VIRTUALENV

    tempdir = tempfile.mkdtemp()
    try:
        if HAS_VIRTUALENV:
            print 'Creating venv...'
            run_command([sys.executable, "-m", 'virtualenv', '-q', '--no-site-packages', '--no-setuptools', '--no-pip',
                         '--no-wheel', VENV])
        else:
            download("https://raw.github.com/pypa/virtualenv/master/virtualenv.py",
                     os.path.join(tempdir, "virtualenv.py"))
            if not run_command([sys.executable, os.path.join(tempdir, "virtualenv.py"), '--no-site-packages',
                                '--no-setuptools', '--no-pip', '--no-wheel', VENV]).strip():
                die('Failed to install virtualenv.')
            HAS_VIRTUALENV = True

        run_command(['sh', 'tools/with_venv.sh', 'python', PIP_DEPS],
                    redirect_output=False)

        print 'done.'
    finally:
        shutil.rmtree(tempdir)
    print 'done.'


def _detect_python_version(venv):
    lib_dir = os.path.join(venv, "lib")
    for pathname in os.listdir(lib_dir):
        if pathname.startswith('python'):
            return pathname
    raise Exception('Unable to detect Python version')


def print_help():
    help = """
 Pilot development environment setup is complete.

 Pilot development uses virtualenv to track and manage Python dependencies
 while in development and testing.

 To activate the Pilot virtualenv for the extent of your current shell session
 you can run:

 $ source .venv/bin/activate

 Or, if you prefer, you can run commands in the virtualenv on a case by case
 basis by running:

 $ tools/with_venv.sh <your command>

 Also, make test will automatically use the virtualenv.
    """
    print help


if __name__ == '__main__':

    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    create_virtualenv()
    print_help()
