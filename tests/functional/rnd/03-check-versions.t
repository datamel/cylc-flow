#!/usr/bin/env bash
# THIS FILE IS PART OF THE CYLC SUITE ENGINE.
# Copyright (C) NIWA & British Crown (Met Office) & Contributors.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------
# Test cylc check-versions
# WARNING: This is testing your remote platform setup, if you do not
#          have the exactly same version of Cylc installed locally and
#          remotely the test will fail.
export REQUIRE_PLATFORM='loc:remote fs:indep'
. "$(dirname "$0")/test_header"
set_test_number 3
#-------------------------------------------------------------------------------
init_suite "${TEST_NAME_BASE}" <<__FLOW__
[scheduler]
    [[events]]
        abort on timeout = True
        timeout=PT30S
[scheduling]
    [[graph]]
        R1 = foo
[runtime]
    [[foo]]
        platform = $CYLC_TEST_PLATFORM
__FLOW__

run_ok "${TEST_NAME_BASE}-validate" cylc validate "${SUITE_NAME}"

TEST_NAME="${TEST_NAME_BASE}-check"
run_ok "${TEST_NAME}" cylc check-versions "${SUITE_NAME}"

contains_ok "${TEST_NAME}.stdout" <<__HERE__
$CYLC_TEST_PLATFORM: $(cylc version)
__HERE__

purge
