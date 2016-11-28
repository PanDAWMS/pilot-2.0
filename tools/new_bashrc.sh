#!/usr/bin/env bash

lsetup python

if [ ! -f /repo/.venv/bin/activate ];then
    python /repo/tools/install_venv.py
fi

source /repo/.venv/bin/activate
