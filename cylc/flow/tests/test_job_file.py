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
from tempfile import TemporaryFile, TemporaryDirectory
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

    @mock.patch("cylc.flow.job_file.get_remote_suite_run_dir")
    def test_write_io_error(self, mocked_get_remote_suite_run_dir):

        job_conf = {
            "host": "localhost",
            "owner": "me",
            "suite_name": "farm_noises",
            "remote_suite_d": "remote/suite/dir",
            "uuid_str": "neigh"
        }
        mocked_get_remote_suite_run_dir.return_value = "run/dir"

        local_job_file_path = "blah/dee/blah"

        with mock.patch("builtins.open", mock.mock_open()) as mock_file:
            mock_file.side_effect = IOError()

            with assertRaises(JobFileWriter().write(local_job_file_path, job_conf), OSError):
                mock_file.assert_called_with("blah/dee/blah.tmp", 'w')


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

    @mock.patch.dict(
        "os.environ", {'CYLC_SUITE_DEF_PATH': 'cylc/suite/def/path'})
    @mock.patch("cylc.flow.job_file.get_remote_suite_work_dir")
    def test_write_suite_environment(self, mocked_get_remote_suite_work_dir):
        """Test suite environment is correctly written in jobscript"""
        self.maxDiff = None
        # set some suite environment conditions
        # mocked_environ.return_value="cylc/suite/def/path"
        mocked_get_remote_suite_work_dir.return_value = "work/dir"
        cylc.flow.flags.debug = True
        cylc.flow.flags.verbose = True
        self.suite_env = {'CYLC_UTC': 'True',
                          'CYLC_CYCLING_MODE': 'integer'}

        JobFileWriter.set_suite_env(self, self.suite_env)
        # suite env not correctly setting...check this
        expected = ('\n\ncylc__job__inst__cylc_env() {\n    # CYLC SUITE '
                    'ENVIRONMENT:\n\n    export CYLC_SUITE_RUN_DIR='
                    '"cylc-run/farm_noises"\n    '
                    'CYLC_SUITE_WORK_DIR_ROOT="work/dir"\n    export '
                    'CYLC_SUITE_DEF_PATH="remote/suite/dir"\n    export '
                    'CYLC_SUITE_DEF_PATH_ON_SUITE_HOST="cylc/suite/def/path"\n'
                    '    export CYLC_SUITE_UUID="neigh"')
        job_conf = {
            "host": "localhost",
            "owner": "me",
            "suite_name": "farm_noises",
            "remote_suite_d": "remote/suite/dir",
            "uuid_str": "neigh"
        }
        rund = "cylc-run/farm_noises"
        with io.StringIO() as fake_file:

            JobFileWriter()._write_suite_environment(fake_file, job_conf, rund)
            self.assertEqual(fake_file.getvalue(), expected)
    
    def test_write_script(self):
        expected = (
            "\n\ncylc__job__inst__init_script() {\n# INIT-SCRIPT:\n"
            "This is the init script\n}\n\ncylc__job__inst__env_script()"
            " {\n# ENV-SCRIPT:\nThis is the env script\n}\n\n"
            "cylc__job__inst__err_script() {\n# ERR-SCRIPT:\nThis is the err "
            "script\n}\n\ncylc__job__inst__pre_script() {\n# PRE-SCRIPT:\n"
            "This is the pre script\n}\n\ncylc__job__inst__script() {\n"
            "# SCRIPT:\nThis is the script\n}\n\ncylc__job__inst__post_script"
            "() {\n# POST-SCRIPT:\nThis is the post script\n}\n\n"
            "cylc__job__inst__exit_script() {\n# EXIT-SCRIPT:\n"
            "This is the exit script\n}")

        job_conf = {
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


    def test_write_task_environment(self):
        """Test task environment is correctly written in jobscript"""
        # set some task environment conditions
        expected = ('\n\n    # CYLC TASK ENVIRONMENT:\n    '
                    'export CYLC_TASK_JOB="1/moo/01"\n    export '
                    'CYLC_TASK_NAMESPACE_HIERARCHY="r o o t   '
                    'b a a   m o o"\n    export CYLC_TASK_DEPENDENCIES'
                    '="moo neigh quack"\n    export CYLC_TASK_TRY_NUMBER='
                    '1\n    export param_env_tmpl_1="moo"\n    '
                    'export param_env_tmpl_2="baa"\n    export '
                    'CYLC_TASK_PARAM_duck="quack"\n    export '
                    'CYLC_TASK_PARAM_mouse="squeak"\n    '
                    'CYLC_TASK_WORK_DIR_BASE=\'farm_noises/work_d\'\n}')
        job_conf = {
            "job_d": "1/moo/01",
            "namespace_hierarchy": "root baa moo",
            "dependencies": ['moo', 'neigh', 'quack'],
            "try_num": 1,
            "param_env_tmpl": {"param_env_tmpl_1": "moo",
                               "param_env_tmpl_2": "baa"},
            "param_var": {"duck": "quack",
                          "mouse": "squeak"},
            "work_d":"farm_noises/work_d"
        }
        with io.StringIO() as fake_file:

            JobFileWriter()._write_task_environment(fake_file, job_conf)
            self.assertEqual(fake_file.getvalue(), expected)


    def test_write_runtime_environment(self):

        expected = (
            '\n\ncylc__job__inst__user_env() {\n    # TASK RUNTIME '
            'ENVIRONMENT:\n    export cow sheep duck\n'
            '    cow=~/"moo"\n    sheep=~baa/"baa"\n    '
            'duck=~quack\n}')
        job_conf = {
            'environment': {'cow':'~/moo', 
            'sheep': '~baa/baa', 
            'duck': '~quack'}
        }
        with io.StringIO() as fake_file:

            JobFileWriter()._write_runtime_environment(fake_file, job_conf)

            self.assertEqual(fake_file.getvalue(), expected)


    def test_write_epilogue(self):

        expected = ('\n\n. \"cylc-run/farm_noises/.service/etc/job.sh\"\n'
                    'cylc__job__main\n\n#EOF: 1/moo/01\n')
        job_conf = {'job_d': "1/moo/01"}
        run_d = "cylc-run/farm_noises"
        with io.StringIO() as fake_file:

            JobFileWriter()._write_epilogue(fake_file, job_conf, run_d)

            self.assertEqual(fake_file.getvalue(), expected)
    
    @mock.patch("cylc.flow.job_file.JobFileWriter._get_host_item")
    def test_write_global_init_scripts(self, mocked_get_host_item):

        mocked_get_host_item.return_value = (
            'global init-script = \n'
            'export COW=moo\n'
            'export PIG=oink\n'
            'export DONKEY=HEEHAW\n'
        )
        job_conf = {}
        expected = ('\n\ncylc__job__inst__global_init_script() {\n'
                    '# GLOBAL-INIT-SCRIPT:\nglobal init-script = \nexport '
                    'COW=moo\nexport PIG=oink\nexport DONKEY=HEEHAW\n\n}')
        with io.StringIO() as fake_file:

            JobFileWriter()._write_global_init_script(fake_file, job_conf)
            self.assertEqual(fake_file.getvalue(), expected)

        

if __name__ == '__main__':
    unittest.main()
