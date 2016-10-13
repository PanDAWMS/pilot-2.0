I. Setup development environment for the first time:
 a) Fork to create a personal repository.
 b) Clone the presonal repository:
    $ git clone git@github.com:<personal_repo>/pilot-2.0.git
 c) Configure git:
    $ git config ---global user.name='<name>'
    $ git config ---global user.email='<email>'
    $ ./tools/configure_git.sh
    note: Here 'flake8' pattern checking hook is added.
 d) Setup both push/pull remotes for origin (your private account) and upstream (official repository):
    $ git remote add upstream git@github.com:PanDAWMS/pilot-2.0.git
    $ git remote set-url --push upstream git@xxxxx:PanDAWMS/pilot-2.0.git
    $ git remote -v
       origin  git@github.com:wguanicedew/pilot-2.0.git (fetch)
       origin  git@github.com:wguanicedew/pilot-2.0.git (push)
       upstream        git@github.com:PanDAWMS/pilot-2.0.git (fetch)
       upstream        git@xxxxxx:PanDAWMS/pilot-2.0.git (push)
 e) Install virtalenv:
   $ python tools/install_venv.py
   Or install as external libraries:
   $ python tools/install_external.py
 f) Generate personal access tokens
   Generate a api tokent in github Settings --> Person access tokens
   Save the token in local .githubkey.

II. Setup development environment:
 a) If virtualenv is used:
   $ source .venv/bin/activate
    Or if external libraries is used:
    source tools/setup_dev.sh

III. Developing:
 a) Create dev/patch/hotfix branch(based on next/master/master)
   $ tools/create-dev-branch <ticketnumber> <branch description>
   $ tools/create-patch-branch <ticketnumber> <branch description>
   $ tools/create-hotfix-branch <ticketnumber> <branch description>
 b) Submit merge pull request:
   $ tools/submit-merge

IV. Local Test
 a) Pattern Validation
   flake8
 b) Run all test instance
   nosetests -v
 c) Run only one test file 
   nosetests -v lib/pilot/test/mock_test.py
 d) Run only one test class
   nosetests -v lib/pilot/test/mock_test.py:TestMock
 e) Run only one test function
   nosetests -v lib/pilot/test/mock_test.py:TestMock.test_mock
