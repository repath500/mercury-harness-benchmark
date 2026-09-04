#!/bin/bash
set -euo pipefail

#!/bin/bash
        set -uo pipefail -x

        cd /testbed

        #We run all of the repo-specific setup commands (If any exist)


        #We then re-run any repo-specific install commands
        pip install -e .

        # First we reset tracked files touched by the FeatBench test patch.
        git checkout c37bef7addeafd01b5939215b046654e32954031 dvc/testing/api_tests.py tests/unit/fs/test_dvc.py tests/unit/fs/test_dvcfs.py

        # Remove only untracked files the FeatBench test patch itself touches.
        # This preserves new source files added by the model/oracle patch.
        # Remove only untracked files the FeatBench test patch touches.
for path in dvc/testing/api_tests.py tests/unit/fs/test_dvc.py tests/unit/fs/test_dvcfs.py; do
    if [ -e "$path" ] && ! git ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
        rm -rf -- "$path"
    fi
done

        #Then we apply the test patch given to us by featbench
        echo 'diff --git a/dvc/testing/api_tests.py b/dvc/testing/api_tests.py
index 1111111..2222222 100644
--- a/dvc/testing/api_tests.py
+++ b/dvc/testing/api_tests.py
@@ -32,12 +32,13 @@ def test_open(self, tmp_dir, dvc, remote):
         "fs_kwargs",
         [
             {},
-            {"url": "{path}"},
-            {"url": "{path}", "rev": "{default_branch}"},
-            {"url": "file://{posixpath}"},
-            {"url": "file://{posixpath}", "rev": "{default_branch}"},
+            {"repo": "{path}"},
+            {"repo": "{path}", "rev": "{default_branch}"},
+            {"repo": "file://{posixpath}"},
+            {"repo": "file://{posixpath}", "rev": "{default_branch}"},
+            {"url": "{path}"},  # test for backward compatibility
         ],
-        ids=["current", "local", "local_rev", "git", "git_rev"],
+        ids=["current", "local", "local_rev", "git", "git_rev", "local_url"],
     )
     def test_filesystem(
         self,
@@ -59,6 +60,8 @@ def test_filesystem(
         if clear_cache:
             remove(dvc.cache.repo.path)

+        if repo := fs_kwargs.get("repo"):
+            fs_kwargs["repo"] = repo.format(path=tmp_dir, posixpath=tmp_dir.as_posix())
         if url := fs_kwargs.get("url"):
             fs_kwargs["url"] = url.format(path=tmp_dir, posixpath=tmp_dir.as_posix())
         if rev := fs_kwargs.get("rev"):
diff --git a/tests/unit/fs/test_dvc.py b/tests/unit/fs/test_dvc.py
index 1111111..2222222 100644
--- a/tests/unit/fs/test_dvc.py
+++ b/tests/unit/fs/test_dvc.py
@@ -696,3 +696,20 @@ def test_fsid_url(erepo_dir):
         fs = DVCFileSystem(repo=dvc)
         assert fs.fsid != old_fsid
         assert fs.fsid == "dvcfs_" + tokenize(url, erepo_dir.scm.get_rev())
+
+
+@pytest.mark.parametrize(
+    "fs_kwargs",
+    [
+        lambda tmp_dir, dvc: {},  # noqa: ARG005
+        lambda tmp_dir, dvc: {"repo": tmp_dir},  # noqa: ARG005
+        lambda tmp_dir, dvc: {"repo": os.fspath(tmp_dir)},  # noqa: ARG005
+        lambda tmp_dir, dvc: {"url": tmp_dir},  # noqa: ARG005
+        lambda tmp_dir, dvc: {"url": os.fspath(tmp_dir)},  # noqa: ARG005
+        lambda tmp_dir, dvc: {"repo": dvc},  # noqa: ARG005
+    ],
+)
+def test_init_arg(tmp_dir, dvc, fs_kwargs):
+    fs = DVCFileSystem(**fs_kwargs(tmp_dir, dvc))
+
+    assert fs.repo.root_dir == dvc.root_dir
diff --git a/tests/unit/fs/test_dvcfs.py b/tests/unit/fs/test_dvcfs.py
index 1111111..2222222 100644
--- a/tests/unit/fs/test_dvcfs.py
+++ b/tests/unit/fs/test_dvcfs.py
@@ -779,7 +779,7 @@ def test_maxdepth(tmp_dir, dvc, scm):
         commit="add dir",
     )

-    fs = DVCFileSystem(url=tmp_dir)
+    fs = DVCFileSystem(tmp_dir)
     fs.get("dir", "dir1", recursive=True, maxdepth=1)
     assert (tmp_dir / "dir1").read_text() == {"file1": "file1"}

@@ -803,3 +803,25 @@ def test_maxdepth(tmp_dir, dvc, scm):
             "subdir2": {"file3": "file3", "subdir3": {"file4": "file4"}},
         },
     }
+
+
+@pytest.mark.parametrize(
+    "fs_args",
+    [
+        lambda tmp_dir, dvc: ((), {}),  # noqa: ARG005
+        lambda tmp_dir, dvc: ((dvc,), {}),  # noqa: ARG005
+        lambda tmp_dir, dvc: ((tmp_dir,), {}),  # noqa: ARG005
+        lambda tmp_dir, dvc: ((str(tmp_dir),), {}),  # noqa: ARG005
+        lambda tmp_dir, dvc: ((), {"repo": tmp_dir}),  # noqa: ARG005
+        lambda tmp_dir, dvc: ((), {"repo": os.fspath(tmp_dir)}),  # noqa: ARG005
+        # url= is deprecated, but is still supported for backward compatibility
+        lambda tmp_dir, dvc: ((), {"url": tmp_dir}),  # noqa: ARG005
+        lambda tmp_dir, dvc: ((), {"url": os.fspath(tmp_dir)}),  # noqa: ARG005
+        lambda tmp_dir, dvc: ((), {"repo": dvc}),  # noqa: ARG005
+    ],
+)
+def test_init_arg(tmp_dir, dvc, fs_args):
+    args, kwargs = fs_args(tmp_dir, dvc)
+    fs = DVCFileSystem(*args, **kwargs)
+
+    assert fs.repo.root_dir == dvc.root_dir' > /tmp/test_patch.diff
        git apply --check /tmp/test_patch.diff
        git apply /tmp/test_patch.diff

        #Then we run all the tests in the repository
        #start recording terminal output in LOG_FILE
        LOG_FILE=$(mktemp)
        export LOG_FILE
        exec 3>&1 4>&2
        exec > >(tee "$LOG_FILE") 2>&1

        set +x
        python -m pytest -q -rA --tb=no -p no:pretty --timeout=1800 --continue-on-collection-errors --timeout-method=signal dvc/testing/api_tests.py tests/unit/fs/test_dvc.py tests/unit/fs/test_dvcfs.py tests/func/api/test_artifacts.py tests/func/api/test_data.py tests/func/api/test_experiments.py tests/func/api/test_scm.py tests/func/api/test_show.py tests/func/artifacts/test_artifacts.py tests/func/data/db/test_index.py tests/func/experiments/test_apply.py tests/func/experiments/test_diff.py tests/func/experiments/test_experiments.py tests/func/experiments/test_queue.py tests/func/experiments/test_remote.py tests/func/experiments/test_remove.py tests/func/experiments/test_rename.py tests/func/experiments/test_save.py tests/func/experiments/test_set_params.py tests/func/experiments/test_show.py tests/func/experiments/test_stash_exp.py tests/func/experiments/test_utils.py tests/func/metrics/test_diff.py tests/func/metrics/test_show.py tests/func/params/test_diff.py tests/func/params/test_show.py tests/func/parsing/test_errors.py tests/func/parsing/test_foreach.py tests/func/parsing/test_interpolated_entry.py tests/func/parsing/test_matrix.py tests/func/parsing/test_resolver.py tests/func/parsing/test_top_level.py tests/func/plots/test_collect.py tests/func/plots/test_diff.py tests/func/plots/test_modify.py tests/func/plots/test_show.py tests/func/repro/test_repro.py tests/func/repro/test_repro_allow_missing.py tests/func/repro/test_repro_pull.py tests/func/test_add.py tests/func/test_analytics.py tests/func/test_check_ignore.py tests/func/test_checkout.py tests/func/test_cli.py tests/func/test_commit.py tests/func/test_config.py tests/func/test_daemon.py tests/func/test_data_cloud.py tests/func/test_data_status.py tests/func/test_dataset.py tests/func/test_diff.py tests/func/test_download.py tests/func/test_du.py tests/func/test_dvcfile.py tests/func/test_external_repo.py tests/func/test_fs.py tests/func/test_gc.py tests/func/test_get.py tests/func/test_get_url.py tests/func/test_ignore.py tests/func/test_import.py tests/func/test_import_db.py tests/func/test_import_url.py tests/func/test_init.py tests/func/test_install.py tests/func/test_lock.py tests/func/test_lockfile.py tests/func/test_ls.py tests/func/test_ls_url.py tests/func/test_merge_driver.py tests/func/test_move.py tests/func/test_odb.py tests/func/test_remote.py tests/func/test_remove.py tests/func/test_repo.py tests/func/test_repo_index.py tests/func/test_root.py tests/func/test_run.py tests/func/test_run_cache.py tests/func/test_scm.py tests/func/test_scm_context.py tests/func/test_stage.py tests/func/test_stage_load.py tests/func/test_state.py tests/func/test_status.py tests/func/test_update.py tests/func/test_used_objs.py tests/func/test_utils.py tests/func/test_virtual_directory.py tests/func/utils/test_hydra.py tests/func/utils/test_strict_yaml.py tests/integration/plots/test_plots.py tests/integration/plots/test_repo_plots_api.py tests/unit/cli/test_main.py tests/unit/command/ls/test_ls.py tests/unit/command/ls/test_ls_colors.py tests/unit/command/test_add.py tests/unit/command/test_cache.py tests/unit/command/test_checkout.py tests/unit/command/test_compat_flag.py tests/unit/command/test_completion.py tests/unit/command/test_config.py tests/unit/command/test_dag.py tests/unit/command/test_data_status.py tests/unit/command/test_data_sync.py tests/unit/command/test_dataset.py tests/unit/command/test_diff.py tests/unit/command/test_du.py tests/unit/command/test_experiments.py tests/unit/command/test_gc.py tests/unit/command/test_get.py tests/unit/command/test_get_url.py tests/unit/command/test_git_hook.py tests/unit/command/test_help.py tests/unit/command/test_imp.py tests/unit/command/test_imp_url.py tests/unit/command/test_ls_url.py tests/unit/command/test_metrics.py tests/unit/command/test_params.py tests/unit/command/test_plots.py tests/unit/command/test_queue.py tests/unit/command/test_repro.py tests/unit/command/test_stage.py tests/unit/command/test_status.py tests/unit/command/test_studio.py tests/unit/command/test_update.py tests/unit/data/db/test_local.py tests/unit/dependency/test_dependency.py tests/unit/dependency/test_params.py tests/unit/fs/test_base.py tests/unit/fs/test_data.py tests/unit/fs/test_dvc_info.py tests/unit/fs/test_fs.py tests/unit/fs/test_tree.py tests/unit/output/test_annotations.py tests/unit/output/test_load.py tests/unit/output/test_local.py tests/unit/output/test_output.py tests/unit/remote/test_oss.py tests/unit/remote/test_remote.py tests/unit/remote/test_webdav.py tests/unit/remote/test_webhdfs.py tests/unit/render/test_convert.py tests/unit/render/test_image_converter.py tests/unit/render/test_match.py tests/unit/render/test_vega_converter.py tests/unit/repo/experiments/queue/test_celery.py tests/unit/repo/experiments/test_collect.py tests/unit/repo/experiments/test_executor_status.py tests/unit/repo/experiments/test_utils.py tests/unit/repo/plots/test_diff.py tests/unit/repo/test_graph.py tests/unit/repo/test_open_repo.py tests/unit/repo/test_repo.py tests/unit/repo/test_reproduce.py tests/unit/repo/test_scm_context.py tests/unit/scm/test_scm.py tests/unit/stage/test_cache.py tests/unit/stage/test_loader_pipeline_file.py tests/unit/stage/test_run.py tests/unit/stage/test_serialize_pipeline_file.py tests/unit/stage/test_serialize_pipeline_lock.py tests/unit/stage/test_stage.py tests/unit/stage/test_utils.py tests/unit/test_analytics.py tests/unit/test_api.py tests/unit/test_collect.py tests/unit/test_compare.py tests/unit/test_config.py tests/unit/test_context.py tests/unit/test_daemon.py tests/unit/test_dirs.py tests/unit/test_dvcfile.py tests/unit/test_hashinfo.py tests/unit/test_ignore.py tests/unit/test_imports.py tests/unit/test_info.py tests/unit/test_interpolate.py tests/unit/test_lockfile.py tests/unit/test_logger.py tests/unit/test_metrics.py tests/unit/test_params.py tests/unit/test_pathspec_math.py tests/unit/test_progress.py tests/unit/test_prompt.py tests/unit/test_run.py tests/unit/test_rwlock.py tests/unit/test_scm.py tests/unit/test_tabular_data.py tests/unit/ui/test_console.py tests/unit/ui/test_pager.py tests/unit/ui/test_table.py tests/unit/utils/serialize/test_python.py tests/unit/utils/serialize/test_toml.py tests/unit/utils/serialize/test_yaml.py tests/unit/utils/test_cli_parse.py tests/unit/utils/test_collections.py tests/unit/utils/test_executors.py tests/unit/utils/test_fs.py tests/unit/utils/test_humanize.py tests/unit/utils/test_plots.py tests/unit/utils/test_studio.py tests/unit/utils/test_utils.py || true
        python -m pytest -q -rA --tb=no -p no:pretty --timeout=1800 --continue-on-collection-errors --timeout-method=signal tests/integration/test_studio_live_experiments.py || true
        exec 1>&3 2>&4 # stop record
        exec 1>&3 2>&4 # stop record
        # And we reset the test files back to the base commit.
        git checkout c37bef7addeafd01b5939215b046654e32954031 dvc/testing/api_tests.py tests/unit/fs/test_dvc.py tests/unit/fs/test_dvcfs.py
        # Remove only untracked files the FeatBench test patch touches.
for path in dvc/testing/api_tests.py tests/unit/fs/test_dvc.py tests/unit/fs/test_dvcfs.py; do
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
