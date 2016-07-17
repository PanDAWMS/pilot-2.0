#!/bin/bash
# Copyright European Organization for Nuclear Research (CERN)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0OA
#
# Authors:
# - Wen Guan, <wen.guan@cern.ch>, 2016


CurrentDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RootDir="$( dirname "$CurrentDir" )"

export PATH=${RootDir}/tools/externals/usr/bin:$PATH
export PYTHONPATH=${RootDir}/tools/externals/usr/lib/python/site-packages:$PYTHONPATH
export PYTHONPATH=${RootDir}/externals:$PYTHONPATH

