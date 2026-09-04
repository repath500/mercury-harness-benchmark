#!/bin/bash
set -euo pipefail

#!/bin/bash
        set -uo pipefail -x

        cd /testbed

        #We run all of the repo-specific setup commands (If any exist)


        #We then re-run any repo-specific install commands
        pip install -e .

        # First we reset tracked files touched by the FeatBench test patch.
        git checkout 54d7e28c4e81888af6845d10f3388fa8244289ff tests/test_cell_space.py

        # Remove only untracked files the FeatBench test patch itself touches.
        # This preserves new source files added by the model/oracle patch.
        # Remove only untracked files the FeatBench test patch touches.
for path in tests/test_cell_space.py; do
    if [ -e "$path" ] && ! git ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
        rm -rf -- "$path"
    fi
done

        #Then we apply the test patch given to us by featbench
        echo 'diff --git a/tests/test_cell_space.py b/tests/test_cell_space.py
index 1111111..2222222 100644
--- a/tests/test_cell_space.py
+++ b/tests/test_cell_space.py
@@ -583,6 +583,40 @@ def test_cell_collection():
     assert len(cells) == len(collection)


+def test_empty_cell_collection():
+    """Test that CellCollection properly handles empty collections."""
+    rng = random.Random(42)
+
+    # Test initializing with empty collection
+    collection = CellCollection([], random=rng)
+    assert len(collection) == 0
+    assert collection._capacity is None
+    assert list(collection.cells) == []
+    assert list(collection.agents) == []
+
+    # Test selecting from empty collection
+    selected = collection.select(lambda cell: True)
+    assert len(selected) == 0
+    assert selected._capacity is None
+
+    # Test filtering to empty collection
+    n = 10
+    full_collection = CellCollection(
+        [Cell((i,), random=rng) for i in range(n)], random=rng
+    )
+    assert len(full_collection) == n
+
+    # Filter to empty collection
+    empty_result = full_collection.select(lambda cell: False)
+    assert len(empty_result) == 0
+    assert empty_result._capacity is None
+
+    # Test at_most with empty collection
+    at_most_result = full_collection.select(lambda cell: False, at_most=5)
+    assert len(at_most_result) == 0
+    assert at_most_result._capacity is None
+
+
 ### PropertyLayer tests
 def test_property_layer_integration():
     """Test integration of PropertyLayer with DiscrateSpace and Cell."""' > /tmp/test_patch.diff
        git apply --check /tmp/test_patch.diff
        git apply /tmp/test_patch.diff

        #Then we run all the tests in the repository
        #start recording terminal output in LOG_FILE
        LOG_FILE=$(mktemp)
        export LOG_FILE
        exec 3>&1 4>&2
        exec > >(tee "$LOG_FILE") 2>&1

        set +x
        python -m pytest -q -rA --tb=no -p no:pretty --timeout=1800 --continue-on-collection-errors --timeout-method=signal tests/test_cell_space.py tests/test_agent.py tests/test_batch_run.py tests/test_components_matplotlib.py tests/test_datacollector.py tests/test_devs.py tests/test_examples.py tests/test_grid.py tests/test_import_namespace.py tests/test_lifespan.py tests/test_model.py tests/test_solara_viz.py tests/test_space.py || true
        exec 1>&3 2>&4 # stop record
        exec 1>&3 2>&4 # stop record
        # And we reset the test files back to the base commit.
        git checkout 54d7e28c4e81888af6845d10f3388fa8244289ff tests/test_cell_space.py
        # Remove only untracked files the FeatBench test patch touches.
for path in tests/test_cell_space.py; do
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
