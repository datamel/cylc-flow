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

import unittest
import io
from tempfile import TemporaryFile
from unittest import mock

import cylc.flow.flags
from cylc.flow.job_file import JobFileWriter

# List of tilde variable inputs
# input value, expected output value
TILDE_IN_OUT = [('~foo/bar bar', '~foo/"bar bar"'),
                ('~/bar bar', '~/"bar bar"'),
                ('~/a', '~/"a"'),
                ('test', '"test"'),
                ('~', '~'),
                ('~a', '~a')]

#  generic_job_conf = {
    # "suite_name": "farm_noises",
    # "task_id": "baa",
    # "job_d": "1/moo/01",
    # "remote_suite_d": "remote/suite/dir",
    # "batch_system_name": "background",
    # "host": "localhost",
    # "owner": "me",
    # "uuid_str": "neigh",
    # "batch_submit_command_template": "woof",
    # "execution_time_limit": "moo",
    # "namespace_hierarchy": "root baa moo",
    # "job_d": "1/baa/01",
    # "job_file_path": "directory/job",
    # "dependencies": ['moo', 'neigh', 'quack'],
    # "try_num": 1,
    # "param_env_tmpl": {},
    # "param_var": {},
    # "work_d":"remote/work/dir",
    # "environment": {},
    # "init-script": "This is the init script,
    # "env-script": "This is the env script",
    # "err-script": "This is the err script",
    # "pre-script": "This is the pre script",
    # "script": "This is the script",
    # "post-script": "This is the post script",
    # "exit-script": "This is the exit script",
    # "batch_system_conf": {},
    # "directives": {"moo": "foo",
    # "             "cluck": "bar"},
    # "logfiles": [],
#  }

class TestJobFile(unittest.TestCase):
    def test_get_variable_value_definition(self):
        """Test the value for single/tilde variables are correctly quoted"""
        for in_value, out_value in TILDE_IN_OUT:
            res = JobFileWriter._get_variable_value_definition(in_value)
            self.assertEqual(out_value, res)

    @mock.patch("cylc.flow.job_file.glbl_cfg")
    def test_write_prelude_invalid_cylc_command(self, mocked_glbl_cfg):
        job_conf = {
            "batch_system_name": "background",
            "host": "localhost",
            "owner": "me"
        }
        mocked = mock.MagicMock()
        mocked_glbl_cfg.return_value = mocked
        mocked.get_host_item.return_value = 'cylc-testing'
        with self.assertRaises(ValueError) as ex:
            with TemporaryFile(mode="w+") as handle:
                JobFileWriter()._write_prelude(handle, job_conf)
        self.assertIn("bad cylc executable", str(ex.exception))

    def test_write_header(self):
        """Test the header is correctly written"""

        expected = ('#!/bin/bash -l\n#\n# ++++ THIS IS A CYLC TASK JOB SCRIPT '
                    '++++\n# Suite: farm_noises\n# Task: baa\n# Job '
                    'log directory: 1/baa/01\n# Job submit method: '
                    'background\n# Job submit command template: woof\n#'
                    ' Execution time limit: moo')
        job_conf = {
            "batch_system_name": "background",
            "batch_submit_command_template": "woof",
            "execution_time_limit": "moo",
            "suite_name": "farm_noises",
            "task_id": "baa",
            "job_d": "1/baa/01"
        }

        with io.StringIO() as fake_file:

            JobFileWriter()._write_header(fake_file, job_conf)

            self.assertEqual(fake_file.getvalue(), expected)

    def test_write_directives(self):
        """"Test the directives section of job script file is correctly
            written"""
        expected = ('\n\n# DIRECTIVES:\n# @ job_name = farm_noises.baa'
                    '\n# @ output = directory/job.out\n# @ error = directory/'
                    'job.err\n# @ wall_clock_limit = 120,60\n# @ moo = foo'
                    '\n# @ cluck = bar\n# @ queue')
        job_conf = {
            "batch_system_name": "loadleveler",
            "batch_submit_command_template": "test_suite",
            "directives": {"moo": "foo",
                           "cluck": "bar"},
            "suite_name": "farm_noises",
            "task_id": "baa",
            "job_d": "1/test_task_id/01",
            "job_file_path": "directory/job",
            "execution_time_limit": 60
        }
        with io.StringIO() as fake_file:
            JobFileWriter()._write_directives(fake_file, job_conf)
            self.assertEqual(fake_file.getvalue(), expected)

    def test_write_prelude(self):
        """Test the prelude section of job script file is correctly
            written"""
        cylc.flow.flags.debug = True
        expected = ('\nCYLC_FAIL_SIGNALS=\'EXIT ERR TERM XCPU\'\n'
                    'CYLC_VACATION_SIGNALS=\'USR1\'\nexport '
                    'CYLC_DEBUG=true\nexport '
                    'CYLC_VERSION=\'8.0a1\'')
        job_conf = {
            "batch_system_name": "loadleveler",
            "batch_submit_command_template": "test_suite",
            "host": "localhost",
            "owner": "me",
            "directives": {"restart": "yes"},
        }

        with io.StringIO() as fake_file:

            JobFileWriter()._write_prelude(fake_file, job_conf)
            self.assertEqual(fake_file.getvalue(), expected)

    def test_write_script(self):
        self.maxDiff=None
        expected = ("\n\ncylc__job__inst__init_script() {\n# INIT-SCRIPT:\n"
            "This is the init script\n}"
            "\n\ncylc__job__inst__env_script() {\n# ENV-SCRIPT:"
            "\nThis is the env script\n}\n"
            "\n\ncylc__job__inst__err_script() {\n# ERR-SCRIPT:"
            "\nThis is the err script\n}"
            "\n\ncylc__job__inst__pre_script() {\n# PRE-SCRIPT:"
            "\nThis is the pre script\n}\n"
            "\n\ncylc__job__inst__script() {\n# SCRIPT:"
            "\nThis is the script\n}"
            "\ncylc__job__inst__post_script() {\n# POST-SCRIPT:"
            "\nThis is the post script\n}\n"
            "\n\ncylc__job__inst__exit_script() {\n# EXIT-SCRIPT:"
            "\nThis is the exit script\n}\n"
        )

        job_conf= {
            "init-script": "This is the init script",
            "env-script": "This is the env script",
            "err-script": "This is the err script",
            "pre-script": "This is the pre script",
            "script": "This is the script",
            "post-script": "This is the post script",
            "exit-script": "This is the exit script",        
        }

        with io.StringIO() as fake_file:

            JobFileWriter()._write_script(fake_file, job_conf)

            self.assertEqual(fake_file.getvalue(), expected)

    
    
    # def test_write_epilogue(self):


if __name__ == '__main__':
    unittest.main()
