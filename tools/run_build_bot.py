# Copyright European Organization for Nuclear Research (CERN)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Authors:
# - Martin Barisits, <martin.barisits@cern.ch>, 2015
# - Wen Guan, <wen.guan@cern.ch>, 2016

import commands
import datetime
import json
import os
import requests
import sys
import subprocess
import time
import errno
import re

try:
    import pydevd
    pydevd.settrace('Complynx-HP.cern.ch', port=6580, stdoutToServer=True, stderrToServer=True)
except ImportError:
    pass


requests.packages.urllib3.disable_warnings()

project_url = "https://api.github.com/repos/PanDAWMS/pilot-2.0/pulls"
split_str = "\n####PILOT##ATUO##TEST####\n"
pid_file = os.path.abspath(os.path.expanduser('/tmp/pilot_test.pid'))
states_file = '/tmp/pilotbuildbot.states'
github_keyfile = '.githubkey'

noqa_regexp = re.compile('^(?i)\+((.*#\s*(NOQA):?\s*(.*))|(\s*#\s*(flake8):\s*noqa\s*))$')


class ProcessRunningException(BaseException):
    pass


class PidFile:
    def __init__(self, path, log=sys.stdout.write, warn=sys.stderr.write):
        self.__pid_file = path
        self.__log = log
        self.__warn = warn

    def __enter__(self):
        try:
            self.__pid_fd = os.open(self.__pid_file, os.O_CREAT | os.O_WRONLY | os.O_EXCL)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pid = self._check()
                if pid:
                    self.__pid_fd = None
                    raise ProcessRunningException('process already running in %s as pid %s' % (self.__pid_file, pid))
                else:
                    os.remove(self.__pid_file)
                    self.__warn('removed staled lockfile %s' % self.__pid_file)
                    self.__pid_fd = os.open(self.__pid_file, os.O_CREAT | os.O_WRONLY | os.O_EXCL)
            else:
                raise

        os.write(self.__pid_fd, str(os.getpid()))
        os.close(self.__pid_fd)
        return self

    def __exit__(self, t, e, tb):
        # return false to raise, true to pass
        if t is None:
            # normal condition, no exception
            self._remove()
            return True
        elif t is ProcessRunningException:
            # do not remove the other process lockfile
            return False
        else:
            # other exception
            if self.__pid_fd:
                # this was our lockfile, removing
                self._remove()
            return False

    def _remove(self):
        os.remove(self.__pid_file)

    def _check(self):
        """
        check if a process is still running the process id is expected to be in pidfile, which should exist. if it
        is still running, returns the pid, if not, return False.
        """
        with open(self.__pid_file, 'r') as f:
            try:
                pidstr = f.read()
                pid = int(pidstr)
            except ValueError:
                # not an integer
                self.__log("not an integer: %s" % pidstr)
                return False
            try:
                os.kill(pid, 0)
            except OSError:
                self.__log("can't deliver signal to %s" % pid)
                return False
            else:
                return pid


def needs_testing(merge_request):
    needs_testing = True

    issue_url = merge_request['issue_url']
    resp = requests.get(url=issue_url)
    issue = json.loads(resp.text)
    labels = [label['name'] for label in issue['labels']]

    pushed_at = merge_request['head']['repo']['pushed_at']
    updated_at = issue['updated_at']

    pushed_at_time = time.mktime(datetime.datetime.strptime(pushed_at, "%Y-%m-%dT%H:%M:%SZ").timetuple())
    updated_at_time = time.mktime(datetime.datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%SZ").timetuple())

    if pushed_at_time < updated_at_time and ('Tests: OK' in labels or 'Tests: FAIL' in labels):
        needs_testing = False
    return needs_testing


def update_pull_request(url, token, data):
    result = requests.post(url=url,
                           headers={"Content-Type": "application/json",
                                    "Authorization": "token %s" % token},
                           data=json.dumps(data))
    if result.status_code == 200 or result.status_code == 201:
        print 'OK'
    else:
        print 'ERROR'
        print result.content


def list_substract(_list, substraction):
    for obj in substraction:
        try:
            _list.remove(obj)
        except ValueError:
            pass


def update_merge_request(merge_request, test_result, found_noqas, comment, token):
    print '  Updating Merge request and putting comment ...'
    resp = requests.get(url=merge_request['issue_url'])
    issue = json.loads(resp.text)
    labels = [label['name'] for label in issue['labels']]

    list_substract(labels, ['Tests: OK', 'Tests: FAIL', 'Tests: NOQA ISSUE'])

    labels.append('Tests: OK' if test_result else 'Tests: FAIL')
    if found_noqas:
        labels.append('Tests: NOQA ISSUE')

    data = {'labels': labels, 'body': '%s%s%s' % (merge_request['body'].split(split_str)[0], split_str, comment)}
    update_pull_request(merge_request['issue_url'], token, data)


def prepare_repository_before_testing():
    # Fetch all
    print '  git fetch --all --prune'
    if commands.getstatusoutput('git fetch --all --prune')[0] != 0:
        print 'Error while fetching all'
        sys.exit(-1)

    # Rebase master/dev
    print '  git rebase origin/dev dev'
    if commands.getstatusoutput('git rebase origin/dev dev')[0] != 0:
        print 'Error while rebaseing dev'
        sys.exit(-1)
    print '  git rebase origin/master master'
    if commands.getstatusoutput('git rebase origin/master master')[0] != 0:
        print 'Error while rebaseing master'
        sys.exit(-1)


def update_venv():
    command = "source .venv/bin/activate;pip install -r tools/pip-requires;pip install -r tools/pip-requires-test;"
    process = subprocess.Popen(['sh', '-c', command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process.communicate()


def test_output(command, title="SOME TEST", test=lambda x: len(x) == 0):
    command = "source .venv/bin/activate;" + command
    process = subprocess.Popen(['sh', '-c', command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = process.communicate()[0]

    test_title = '##### ' + title + ":"

    if test(out):
        return True, test_title + " OK"

    return False, test_title + "\n```\n" + out + "\n```\n"


def get_diff(merge_request):
    resp = requests.get(merge_request['diff_url'], verify=False)
    return resp.text


def test_request(merge_request):
    tests_passed = True
    error_lines = ''

    # Check for Cross Merges
    if merge_request['head']['ref'].lower().startswith('patch'):
        print '  Checking for cross-merges:'
        commits = commands.getoutput('git log master..remotes/%s/%s | grep ^commit' %
                                     (merge_request['head']['label'].split(":")[0],
                                      merge_request['head']['label'].split(":")[1]))
        for commit in commits.splitlines():
            commit = commit.partition(' ')[2]
            if commands.getstatusoutput('git branch --contains %s | grep dev' % commit)[0] == 0:
                print '    Found cross-merge problem with commit %s' % commit
                tests_passed = False
                error_lines += '##### CROSS-MERGE TESTS:\n'
                error_lines += '```\n'
                error_lines += 'This patch is suspicious. It looks like there are feature-commits pulled into' \
                               ' the master branch!\n'
                error_lines += '```\n'
                break

    # Checkout the branch to test
    print '  git checkout remotes/%s' % (merge_request['head']['label'].replace(":", "/"))
    if commands.getstatusoutput('git checkout remotes/%s' % (merge_request['head']['label'].replace(":", "/")))[0] != 0:
        print 'Error while checking out branch'
        sys.exit(-1)

    cwd = os.getcwd()
    os.chdir(root_git_dir)
    update_venv()

    tested, message = test_output("nosetests -v", title="UNIT TESTS", test=lambda x: x.endswith("OK\n"))
    error_lines += message
    tests_passed = tests_passed and tested
    tested, message = test_output("flake8 .", title="FLAKE8")
    error_lines += message
    tests_passed = tests_passed and tested

    diff = get_diff(merge_request)

    noqas = ''
    matches = filter(lambda x: len(x) > 0, map(lambda x: noqa_regexp.findall(x), diff.split("\n")))
    for match in matches:
        noqas += match[0][0]
        if len(match[0][3]) == 0:
            tests_passed = False

    error_lines += noqas

    found_noqas = noqas != ''

    error_lines = '#### BUILD-BOT TEST RESULT: ' + ('OK' if tests_passed else 'FAIL') + \
                  ('\nWARNING: FOUND NOQAS!' if found_noqas else '') + '\n\n' +\
                  (error_lines if len(error_lines) else '')

    os.chdir(cwd)

    return error_lines, tests_passed, found_noqas


def update_tests(merge_request, token):
    print 'Starting testing for MR %s ...' % merge_request['head']['label']
    # Add remote to user
    commands.getstatusoutput('git remote add %s %s' % (merge_request['head']['label'].split(":")[0],
                                                       merge_request['head']['repo']['git_url']))

    prepare_repository_before_testing()
    error_lines, tests_passed, noqas = test_request(merge_request)

    update_merge_request(merge_request=merge_request, test_result=tests_passed, comment=error_lines, token=token,
                         found_noqas=noqas)

    # Checkout original master
    print '  git checkout master'
    if commands.getstatusoutput('git checkout master')[0] != 0:
        print 'Error while checking out master'
        sys.exit(-1)

with PidFile(pid_file):

    root_git_dir = commands.getstatusoutput('git rev-parse --show-toplevel')[1]
    os.chdir(root_git_dir)

    # Load private_token
    print 'Loading private token ...'
    try:
        with open(github_keyfile, 'r') as f:
            private_token = f.readline().strip()
    except IOError:
        print 'No github keyfile found at ' + os.path.join(os.getcwd(), github_keyfile)
        sys.exit(-1)

    # Load state file
    print 'Loading state file ...'
    try:
        with open(states_file) as data_file:
            states = json.load(data_file)
    except IOError or ValueError:
        states = {}

    # Get all open merge requests
    print 'Getting all open merge requests ...'
    resp = requests.get(url=project_url, params={'state': 'open'})
    merge_request_list = json.loads(resp.text)
    for merge_request in merge_request_list:
        print 'Checking MR %s -> %s if it needs testing ...' % (merge_request['head']['label'],
                                                                merge_request['base']['label'])
        if 'dev' in merge_request['base']['label'] and needs_testing(merge_request):
            print 'YES'
            update_tests(merge_request=merge_request, token=private_token)
        else:
            print 'NO'

    print 'Writing state file ...'
    with open(states_file, 'w') as outfile:
        json.dump(states, outfile)
