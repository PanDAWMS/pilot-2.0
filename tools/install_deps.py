import sys
import os
import tempfile
import shutil
import subprocess
import time
import imp
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

MY_DIR = os.path.dirname(__file__)
ROOT = os.path.dirname(MY_DIR)
PIP_REQUIRES = os.path.join(MY_DIR, 'pip-requires')
PIP_REQUIRES_TEST = os.path.join(MY_DIR, 'pip-requires-test')


def die(message, *args):
    print >> sys.stderr, message % args
    sys.exit(1)


def has_module(mod):
    try:
        imp.find_module(mod)
        return True
    except ImportError:
        return False

HAS_PIP = has_module('pip')
HAS_SETUP = has_module('setuptools')


def download(url, to_path):
    print 'Downloading %s into %s' % (url, to_path)
    req = urlopen(url)
    with open(to_path, 'wb') as fp:
        for line in req:
            fp.write(line)
    return to_path


def run_command(cmd, redirect_output=True, check_exit_code=True, shell=False, prefix=None):
    """
    Runs a command in an out-of-process shell, returning the
    output of that command.  Working directory is ROOT.
    """
    if prefix:
        cmd.append("--prefix=" + prefix)
    if shell:
        cmd = ['sh', '-c', cmd]
    print cmd
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE if redirect_output else None)
    output = proc.communicate()[0]
    if check_exit_code and proc.returncode != 0:
        # print("ec = %d " % proc.returncode)
        raise subprocess.CalledProcessError(proc.returncode, ' '.join(cmd), output)
    return output


def try_setup(tempdir, url, name, prefix):
    print 'Setting up ' + name
    i = 0
    while True:
        try:
            run_command([sys.executable, download(url, os.path.join(tempdir, name))], prefix=prefix)
        except subprocess.CalledProcessError:
            if i < 5:
                time.sleep(2)
                i += 1
                print 'Failed, next try...'
                continue
            raise
        break


def setup_paths(prefix):
    lib_dir = os.path.join(prefix, "lib")
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


def install_deps(prefix=None, no_setup=False):
    tempdir = tempfile.mkdtemp()
    try:
        if not HAS_SETUP and not no_setup:
            try_setup(tempdir, "https://bootstrap.pypa.io/ez_setup.py", "ez_setup.py", prefix)

        if not HAS_PIP:
            try_setup(tempdir, "https://bootstrap.pypa.io/get-pip.py", "get-pip.py", prefix)

        print 'Installing dependencies with pip (this can take a while)...'

        if prefix:
            setup_paths(prefix)

        run_command([sys.executable, '-m', 'pip', 'install', '-r', PIP_REQUIRES],
                    redirect_output=False, prefix=prefix)
        run_command([sys.executable, '-m', 'pip', 'install', '-r', PIP_REQUIRES_TEST],
                    redirect_output=False, prefix=prefix)
    finally:
        shutil.rmtree(tempdir)


if __name__ == "__main__":
    try:
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('-s', "--no_setup", action="store_true")
        parser.add_argument('-p', "--prefix", default=None, type=lambda x: x if os.path.isdir(x) else None)
        arg = parser.parse_args(sys.argv[1:])
    except ImportError:
        import optparse

        parser = optparse.OptionParser()
        parser.add_option('-s', "--no_setup", action="store_true")
        parser.add_option('-p', "--prefix", default=None, type="string")
        arg = parser.parse_args()
        if arg.no_setup and not os.path.isdir(arg.no_setup):
            arg.no_setup = None

    install_deps(arg.prefix, arg.no_setup)
