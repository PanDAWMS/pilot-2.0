#!/usr/bin/env bash
TOOLS=`dirname $0`
VENV="$TOOLS"/../.venv

function test_and_run {
    ACTIVATE="$1"
    shift
    if [ -f "$ACTIVATE" ];then
        source "$ACTIVATE" && "$@"
        exit $?
    fi
}

# Unix standard installation
test_and_run "$VENV"/bin/activate "$@"
# Windows standard installation
test_and_run "$VENV"/Scripts/activate "$@"


