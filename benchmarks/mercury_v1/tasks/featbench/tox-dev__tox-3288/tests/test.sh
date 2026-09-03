#!/bin/bash
set -euo pipefail

#!/bin/bash
        set -uo pipefail -x

        cd /testbed

        #We run all of the repo-specific setup commands (If any exist)


        #We then re-run any repo-specific install commands
        pip install -e .

        # First we reset tracked files touched by the FeatBench test patch.
        git checkout 406f80887f757ba430c79280ad767492cf046296 tests/config/loader/test_str_convert.py

        # Remove only untracked files the FeatBench test patch itself touches.
        # This preserves new source files added by the model/oracle patch.
        # Remove only untracked files the FeatBench test patch touches.
for path in tests/config/loader/test_str_convert.py; do
    if [ -e "$path" ] && ! git ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
        rm -rf -- "$path"
    fi
done

        #Then we apply the test patch given to us by featbench
        echo 'diff --git a/tests/config/loader/test_str_convert.py b/tests/config/loader/test_str_convert.py
index 1111111..2222222 100644
--- a/tests/config/loader/test_str_convert.py
+++ b/tests/config/loader/test_str_convert.py
@@ -57,6 +57,21 @@ def test_str_convert_ok(raw: str, value: Any, of_type: type[Any]) -> None:
     assert result == value


+# Tests that can work only with py39 or newer due to type not being subscriptible before
+if sys.version_info >= (3, 9):
+
+    @pytest.mark.parametrize(
+        ("raw", "value", "of_type"),
+        [
+            ("", None, Optional[list[str]]),
+            ("1,2", ["1", "2"], Optional[list[str]]),
+        ],
+    )
+    def test_str_convert_ok_py39(raw: str, value: Any, of_type: type[Any]) -> None:
+        result = StrConvert().to(raw, of_type, None)
+        assert result == value
+
+
 @pytest.mark.parametrize(
     ("raw", "of_type", "exc_type", "msg"),
     [' > /tmp/test_patch.diff
        git apply --check /tmp/test_patch.diff
        git apply /tmp/test_patch.diff

        #Then we run all the tests in the repository
        #start recording terminal output in LOG_FILE
        LOG_FILE=$(mktemp)
        export LOG_FILE
        exec 3>&1 4>&2
        exec > >(tee "$LOG_FILE") 2>&1

        set +x
        python -m pytest -q -rA --tb=no -p no:pretty --timeout=1800 --continue-on-collection-errors --timeout-method=signal tests/config/loader/test_str_convert.py tests/config/cli/test_cli_env_var.py tests/config/cli/test_cli_ini.py tests/config/cli/test_parse.py tests/config/cli/test_parser.py tests/config/loader/ini/replace/test_replace.py tests/config/loader/ini/replace/test_replace_env_var.py tests/config/loader/ini/replace/test_replace_os_pathsep.py tests/config/loader/ini/replace/test_replace_os_sep.py tests/config/loader/ini/replace/test_replace_posargs.py tests/config/loader/ini/replace/test_replace_tox_env.py tests/config/loader/ini/replace/test_replace_tty.py tests/config/loader/ini/test_factor.py tests/config/loader/ini/test_ini_loader.py tests/config/loader/test_loader.py tests/config/loader/test_memory_loader.py tests/config/loader/test_section.py tests/config/source/test_discover.py tests/config/source/test_legacy_toml.py tests/config/source/test_setup_cfg.py tests/config/source/test_source_ini.py tests/config/test_main.py tests/config/test_of_types.py tests/config/test_set_env.py tests/config/test_sets.py tests/config/test_types.py tests/execute/local_subprocess/test_execute_util.py tests/execute/local_subprocess/test_local_subprocess.py tests/execute/test_request.py tests/execute/test_stream.py tests/journal/test_main_journal.py tests/plugin/test_inline.py tests/plugin/test_plugin.py tests/plugin/test_plugin_custom_config_set.py tests/pytest_/test_init.py tests/session/cmd/run/test_common.py tests/session/cmd/test_depends.py tests/session/cmd/test_devenv.py tests/session/cmd/test_exec_.py tests/session/cmd/test_legacy.py tests/session/cmd/test_list_envs.py tests/session/cmd/test_parallel.py tests/session/cmd/test_quickstart.py tests/session/cmd/test_sequential.py tests/session/cmd/test_show_config.py tests/session/cmd/test_state.py tests/session/test_env_select.py tests/session/test_session_common.py tests/test_call_modes.py tests/test_provision.py tests/test_report.py tests/test_run.py tests/test_version.py tests/tox_env/python/pip/req/test_file.py tests/tox_env/python/pip/test_pip_install.py tests/tox_env/python/pip/test_req_file.py tests/tox_env/python/test_python_api.py tests/tox_env/python/virtual_env/package/test_package_cmd_builder.py tests/tox_env/python/virtual_env/package/test_package_pyproject.py tests/tox_env/python/virtual_env/package/test_python_package_util.py tests/tox_env/python/virtual_env/test_virtualenv_api.py tests/tox_env/test_api.py tests/tox_env/test_info.py tests/tox_env/test_register.py tests/tox_env/test_tox_env_api.py tests/util/test_ci.py tests/util/test_cpu.py tests/util/test_graph.py tests/util/test_path.py tests/util/test_spinner.py || true
        python -m pytest -q -rA --tb=no -p no:pretty --timeout=1800 --continue-on-collection-errors --timeout-method=signal tests/tox_env/python/test_python_runner.py || true
        exec 1>&3 2>&4 # stop record
        exec 1>&3 2>&4 # stop record
        # And we reset the test files back to the base commit.
        git checkout 406f80887f757ba430c79280ad767492cf046296 tests/config/loader/test_str_convert.py
        # Remove only untracked files the FeatBench test patch touches.
for path in tests/config/loader/test_str_convert.py; do
    if [ -e "$path" ] && ! git ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
        rm -rf -- "$path"
    fi
done


cd ..
cat > parser.py <<EOF
# /// script
# requires-python = ">=3.11"
# dependencies = ["swebench @ git+https://github.com/radinshayanfar/SWE-bench.git@ec4a42631acca692e56b168268d54296aa52ed24", "datasets==2.16.1", "fastcore<1.11"]
# ///

import sys
import json
import os
import pathlib
from swebench.harness.grading import MAP_REPO_TO_PARSER
from swebench.harness.test_spec.test_spec import make_test_spec
from swebench.harness.constants import ResolvedStatus, EvalType, PASS_TO_PASS, \
                                       FAIL_TO_PASS, KEY_INSTANCE_ID, \
                                       FAIL_ONLY_REPOS, START_TEST_OUTPUT, END_TEST_OUTPUT
from swebench.harness.grading import get_logs_eval, \
                                     get_eval_tests_report, \
                                     get_resolution_status

with open("/tests/config.json", "r") as file:
    datum = json.load(file)

test_spec   = make_test_spec(datum)
report_map = {}
instance_id = datum[KEY_INSTANCE_ID]
report_map[instance_id] = {
    "patch_is_None": False,
    "patch_exists": False,
    "patch_successfully_applied": False,
    "resolved": False,
}
report_map[instance_id]["patch_exists"] = True
test_log_path = os.environ["LOG_FILE"]
with open(test_log_path, 'r+') as f:
    content = f.read()
    f.seek(0)
    f.write(f'{START_TEST_OUTPUT}\n{content}\n{END_TEST_OUTPUT}')
    f.truncate()

from swebench.harness.constants import TestStatus

def resolve_parameterized_from_log(status_map, f2p_tests, p2p_tests, log_path):
    """For tests missing from status_map, scan the raw log for parameterized variants.

    The SWE-bench parser splits lines on whitespace, which breaks when pytest
    parameters contain spaces (e.g. Literal['one', 'two']).  We bypass this by
    matching the known test-name prefix directly against log lines in the -rA
    summary format: "STATUS test_name[...]".
    """
    with open(log_path) as f:
        log_lines = f.read().splitlines()

    passing = (TestStatus.PASSED.value, TestStatus.XFAIL.value)
    failing = (TestStatus.FAILED.value, TestStatus.ERROR.value)

    for test_name in f2p_tests + p2p_tests:
        if test_name in status_map:
            continue

        # Look for parameterized variant lines: "STATUS test_name[..."
        found_any = False
        all_pass = True
        for line in log_lines:
            for status in (*passing, *failing):
                prefix = f"{status} {test_name}["
                if line.startswith(prefix):
                    found_any = True
                    if status in failing:
                        all_pass = False
                    break

        if found_any:
            status_map[test_name] = TestStatus.PASSED.value if all_pass else TestStatus.FAILED.value

    return status_map

eval_status_map, found = get_logs_eval(test_spec, test_log_path)
if found:
    report_map[instance_id]["patch_successfully_applied"] = True
    eval_status_map = resolve_parameterized_from_log(
        eval_status_map,
        test_spec.FAIL_TO_PASS,
        test_spec.PASS_TO_PASS,
        test_log_path,
    )

    eval_ref = {
        KEY_INSTANCE_ID: test_spec.instance_id,
        FAIL_TO_PASS: test_spec.FAIL_TO_PASS,
        PASS_TO_PASS: test_spec.PASS_TO_PASS,
    }

    eval_type = EvalType.FAIL_ONLY if test_spec.repo in FAIL_ONLY_REPOS \
        else EvalType.PASS_AND_FAIL

    report = get_eval_tests_report(
        eval_status_map, eval_ref, eval_type=eval_type
    )
    if get_resolution_status(report) == ResolvedStatus.FULL.value:
        report_map[instance_id]["resolved"] = True
    report_map[instance_id]["tests_status"] = report

json.dump(report_map, open("/logs/verifier/report.json", "w"), indent=4)

print(f"FeatBench results starts here")
if report_map[instance_id]["resolved"]:
    print("PASSED")
else:
    print("FAILED")
print("FeatBench results ends here")
sys.exit(0 if report_map[instance_id]["resolved"] else 1)
EOF

chmod +x parser.py
mkdir -p /logs/verifier

# Run parser and capture its exit code.
set +e
export PATH="/root/.local/bin:$PATH"
uv run parser.py | tee -a "$LOG_FILE"
exit_code=$?
set -e

# Reward logging for Harbor.
if [ "${exit_code}" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "${exit_code}"
