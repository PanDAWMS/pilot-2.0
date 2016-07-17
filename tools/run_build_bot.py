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

requests.packages.urllib3.disable_warnings()

project_url = "https://api.github.com/repos/PanDAWMS/pilot-2.0/pulls"
split_str = "\n####PILOT##ATUO##TEST####\n"


def needs_testing(mr):
    needs_testing = True

    issue_url = mr['issue_url']
    resp = requests.get(url=issue_url)
    issue = json.loads(resp.text)
    labels = [label['name'] for label in issue['labels']]

    pushed_at = mr['head']['repo']['pushed_at']
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


def update_merg_request(mr, test_result, comment, token):
    print '  Updating Merge request and putting comment ...'
    resp = requests.get(url=mr['issue_url'])
    issue = json.loads(resp.text)
    labels = [label['name'] for label in issue['labels']]
    try:
        labels.remove('Tests: OK')
    except:
        pass
    try:
        labels.remove('Tests: FAIL')
    except:
        pass

    if test_result:
        labels.append('Tests: OK')
    else:
        labels.append('Tests: FAIL')

    data = {'labels': labels, 'body': '%s%s%s' % (mr['body'].split(split_str)[0], split_str, comment)}
    update_pull_request(mr['issue_url'], token, data)


def start_test(mr, token):
    tests_passed = True
    error_lines = []
    print 'Starting testing for MR %s ...' % mr['head']['label']
    # Add remote to user
    commands.getstatusoutput('git remote add %s %s' % (mr['head']['label'].split(":")[0], mr['head']['repo']['git_url']))

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

    # Check for Cross Merges
    if mr['head']['ref'].lower().startswith('patch'):
        print '  Checking for cross-merges:'
        commits = commands.getoutput('git log master..remotes/%s/%s | grep ^commit' % (mr['head']['label'].split(":")[0], mr['head']['label'].split(":")[1]))
        for commit in commits.splitlines():
            commit = commit.partition(' ')[2]
            if commands.getstatusoutput('git branch --contains %s | grep dev' % commit)[0] == 0:
                print '    Found cross-merge problem with commit %s' % commit
                tests_passed = False
                error_lines.append('##### CROSS-MERGE TESTS:\n')
                error_lines.append('```\n')
                error_lines.append('This patch is suspicious. It looks like there are feature-commits pulled into the master branch!\n')
                error_lines.append('```\n')
                break

    # Checkout the branch to test
    print '  git checkout remotes/%s' % (mr['head']['label'].replace(":", "/"))
    if commands.getstatusoutput('git checkout remotes/%s' % (mr['head']['label'].replace(":", "/")))[0] != 0:
        print 'Error while checking out branch'
        sys.exit(-1)

    command = """
    cd %s; source .venv/bin/activate;
    pip install -r tools/pip-requires;
    pip install -r tools/pip-requires-test;
    find lib -iname "*.pyc" | xargs rm; rm -rf /tmp/.pilot_*/;
    nosetests -v > /tmp/pilot_nose.txt 2> /tmp/pilot_nose.txt;
    flake8 *.py > /tmp/pilot_flake8.txt;
    """ % (root_git_dir)  # NOQA
    print '  %s' % command
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    process.communicate()

    with open('/tmp/pilot_nose.txt', 'r') as f:
        lines = f.readlines()
        if lines[-1] != 'OK\n':
            tests_passed = False
            error_lines.append('##### UNIT TESTS:\n')
            error_lines.append('```\n')
            error_lines.extend(lines)
            error_lines.append('```\n')

    if os.stat('/tmp/pilot_flake8.txt').st_size != 0:
        with open('/tmp/pilot_flake8.txt', 'r') as f:
            lines = f.readlines()
            tests_passed = False
            error_lines.append('##### FLAKE8:\n')
            error_lines.append('```\n')
            error_lines.extend(lines)
            error_lines.append('```\n')

    if tests_passed:
        error_lines.insert(0, '#### BUILD-BOT TEST RESULT: OK\n\n')
    else:
        error_lines.insert(0, '#### BUILD-BOT TEST RESULT: FAIL\n\n')

    update_merg_request(mr=mr, test_result=tests_passed, comment=error_lines, token=token)

    # Checkout original master
    print '  git checkout master'
    if commands.getstatusoutput('git checkout master')[0] != 0:
        print 'Error while checking out master'
        sys.exit(-1)

print 'Checking if a job is currently running ...'
if os.path.isfile('/tmp/pilot_test.pid'):
    # Check if the pid file is older than 90 minutes
    if os.stat('/tmp/pilot_test.pid').st_mtime < time.time() - 60 * 90:
        os.remove('/tmp/pilot_test.pid')
        open('/tmp/pilot_test.pid', 'a').close()
    else:
        sys.exit(-1)
else:
    open('/tmp/pilot_test.pid', 'a').close()

root_git_dir = commands.getstatusoutput('git rev-parse --show-toplevel')[1]

# Load private_token
print 'Loading private token ...'
try:
    with open(root_git_dir + '/.githubkey', 'r') as f:
        private_token = f.readline().strip()
except:
    print 'No github keyfile found at %s' % root_git_dir + '/.githubkey'
    sys.exit(-1)

# Load state file
print 'Loading state file ...'
try:
    with open('/tmp/pilotbuildbot.states') as data_file:
        states = json.load(data_file)
except:
    states = {}

# Get all open merge requests
print 'Getting all open merge requests ...'
resp = requests.get(url=project_url, params={'state': 'open'})
mr_list = json.loads(resp.text)
for mr in mr_list:
    print 'Checking MR %s -> %s if it needs testing ...' % (mr['head']['label'], mr['base']['label']),
    if 'dev' in mr['base']['label'] and needs_testing(mr):
        print 'YES'
        start_test(mr=mr, token=private_token)
    else:
        print 'NO'

print 'Writing state file ...'
with open('/tmp/pilotbuildbot.states', 'w') as outfile:
    json.dump(states, outfile)

os.remove('/tmp/pilot_test.pid')
