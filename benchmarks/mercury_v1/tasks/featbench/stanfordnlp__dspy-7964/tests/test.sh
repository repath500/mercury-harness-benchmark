#!/bin/bash
set -euo pipefail

#!/bin/bash
        set -uo pipefail -x

        cd /testbed

        #We run all of the repo-specific setup commands (If any exist)


        #We then re-run any repo-specific install commands
        pip install -e .

        # First we reset tracked files touched by the FeatBench test patch.
        :

        # Remove only untracked files the FeatBench test patch itself touches.
        # This preserves new source files added by the model/oracle patch.
        # Remove only untracked files the FeatBench test patch touches.
for path in tests/predict/test_best_of_n.py; do
    if [ -e "$path" ] && ! git ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
        rm -rf -- "$path"
    fi
done

        #Then we apply the test patch given to us by featbench
        echo 'diff --git a/tests/predict/test_best_of_n.py b/tests/predict/test_best_of_n.py
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/tests/predict/test_best_of_n.py
@@ -0,0 +1,109 @@
+import pytest
+
+import dspy
+from dspy.predict.predict import Predict
+from dspy.predict.best_of_n import BestOfN
+from dspy.primitives.prediction import Prediction
+from dspy.utils.dummies import DummyLM
+
+
+class DummyModule(dspy.Module):
+
+    def __init__(self, signature, forward_fn):
+        super().__init__()
+        self.predictor = Predict(signature)
+        self.forward_fn = forward_fn
+
+    def forward(self, **kwargs) -> Prediction:
+        return self.forward_fn(self, **kwargs)
+
+
+def test_refine_forward_success_first_attempt():
+    lm = DummyLM([{
+        "answer": "Brussels"
+    }, {
+        "answer": "City of Brussels"
+    }, {
+        "answer": "Brussels"
+    }])
+    dspy.settings.configure(lm=lm)
+    module_call_count = [0]
+
+    def count_calls(self, **kwargs):
+        module_call_count[0] += 1
+        return self.predictor(**kwargs)
+
+    reward_call_count = [0]
+
+    def reward_fn(kwargs, pred: Prediction) -> float:
+        reward_call_count[0] += 1
+        # The answer should always be one word.
+        return 1.0 if len(pred.answer) == 1 else 0.0
+
+    predict = DummyModule("question -> answer", count_calls)
+
+    best_of_n = BestOfN(module=predict,
+                        N=3,
+                        reward_fn=reward_fn,
+                        threshold=1.0)
+    result = best_of_n(question="What is the capital of Belgium?")
+
+    assert result.answer == "Brussels", "Result should be `Brussels`"
+    assert reward_call_count[0] > 0, "Reward function should have been called"
+    assert module_call_count[0] == 3, (
+        "Module should have been called exactly 3 times, but was called %d times"
+        % module_call_count[0])
+
+
+def test_refine_module_default_fail_count():
+    lm = DummyLM([{
+        "answer": "Brussels"
+    }, {
+        "answer": "City of Brussels"
+    }, {
+        "answer": "Brussels"
+    }])
+    dspy.settings.configure(lm=lm)
+
+    def always_raise(self, **kwargs):
+        raise ValueError("Deliberately failing")
+
+    predict = DummyModule("question -> answer", always_raise)
+
+    best_of_n = BestOfN(module=predict,
+                        N=3,
+                        reward_fn=lambda _, __: 1.0,
+                        threshold=0.0)
+    with pytest.raises(ValueError):
+        best_of_n(question="What is the capital of Belgium?")
+
+
+def test_refine_module_custom_fail_count():
+    lm = DummyLM([{
+        "answer": "Brussels"
+    }, {
+        "answer": "City of Brussels"
+    }, {
+        "answer": "Brussels"
+    }])
+    dspy.settings.configure(lm=lm)
+    module_call_count = [0]
+
+    def raise_on_second_call(self, **kwargs):
+        if module_call_count[0] < 2:
+            module_call_count[0] += 1
+            raise ValueError("Deliberately failing")
+        return self.predictor(**kwargs)
+
+    predict = DummyModule("question -> answer", raise_on_second_call)
+
+    best_of_n = BestOfN(module=predict,
+                        N=3,
+                        reward_fn=lambda _, __: 1.0,
+                        threshold=0.0,
+                        fail_count=1)
+    with pytest.raises(ValueError):
+        best_of_n(question="What is the capital of Belgium?")
+    assert module_call_count[0] == 2, (
+        "Module should have been called exactly 2 times, but was called %d times"
+        % module_call_count[0])' > /tmp/test_patch.diff
        git apply --check /tmp/test_patch.diff
        git apply /tmp/test_patch.diff

        #Then we run all the tests in the repository
        #start recording terminal output in LOG_FILE
        LOG_FILE=$(mktemp)
        export LOG_FILE
        exec 3>&1 4>&2
        exec > >(tee "$LOG_FILE") 2>&1

        set +x
        python -m pytest -q -rA --tb=no -p no:pretty --timeout=1800 --continue-on-collection-errors --timeout-method=signal tests/predict/test_best_of_n.py tests/adapters/test_chat_adapter.py tests/adapters/test_json_adapter.py tests/caching/test_caching.py tests/callback/test_callback.py tests/clients/test_embedding.py tests/clients/test_inspect_global_history.py tests/clients/test_lm.py tests/datasets/test_dataset.py tests/docs/test_mkdocs_links.py tests/evaluate/test_evaluate.py tests/evaluate/test_metrics.py tests/metadata/test_metadata.py tests/predict/test_aggregation.py tests/predict/test_chain_of_thought.py tests/predict/test_knn.py tests/predict/test_multi_chain_comparison.py tests/predict/test_parallel.py tests/predict/test_predict.py tests/predict/test_program_of_thought.py tests/predict/test_react.py tests/predict/test_refine.py tests/primitives/test_example.py tests/primitives/test_module.py tests/primitives/test_program.py tests/primitives/test_tool.py tests/signatures/test_adapter_image.py tests/signatures/test_signature.py tests/teleprompt/test_bootstrap.py tests/teleprompt/test_copro_optimizer.py tests/teleprompt/test_ensemble.py tests/teleprompt/test_knn_fewshot.py tests/teleprompt/test_random_search.py tests/teleprompt/test_utils.py tests/utils/test_asyncify.py tests/utils/test_saving.py tests/utils/test_streaming.py || true
        exec 1>&3 2>&4 # stop record
        exec 1>&3 2>&4 # stop record
        # And we reset the test files back to the base commit.
        :
        # Remove only untracked files the FeatBench test patch touches.
for path in tests/predict/test_best_of_n.py; do
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
