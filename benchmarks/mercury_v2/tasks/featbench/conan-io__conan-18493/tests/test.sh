#!/bin/bash
set -euo pipefail

#!/bin/bash
        set -uo pipefail -x

        cd /testbed

        #We run all of the repo-specific setup commands (If any exist)


        #We then re-run any repo-specific install commands
        pip install -e .

        # First we reset tracked files touched by the FeatBench test patch.
        git checkout ff5c4ffcefa632e11474221b014b23b0c9a3de22 test/integration/workspace/test_workspace.py

        # Remove only untracked files the FeatBench test patch itself touches.
        # This preserves new source files added by the model/oracle patch.
        # Remove only untracked files the FeatBench test patch touches.
for path in test/integration/workspace/test_workspace.py; do
    if [ -e "$path" ] && ! git ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
        rm -rf -- "$path"
    fi
done

        #Then we apply the test patch given to us by featbench
        echo 'diff --git a/test/integration/workspace/test_workspace.py b/test/integration/workspace/test_workspace.py
index 1111111..2222222 100644
--- a/test/integration/workspace/test_workspace.py
+++ b/test/integration/workspace/test_workspace.py
@@ -7,10 +7,12 @@

 from conan.api.subapi.workspace import WorkspaceAPI
 from conan.test.assets.genconanfile import GenConanfile
+from conan.test.utils.mocks import ConanFileMock
 from conan.test.utils.scm import create_local_git_repo
 from conan.test.utils.test_files import temp_folder
 from conan.test.utils.tools import TestClient
 from conan.internal.util.files import save_files
+from conan.tools.files import replace_in_file

 WorkspaceAPI.TEST_ENABLED = "will_break_next"

@@ -137,14 +139,14 @@ def set_version(self):

                 class MyWorkspace(Workspace):
                     def packages(self):
-                        result = {}
+                        result = []
                         for f in os.listdir(self.folder):
                             if os.path.isdir(os.path.join(self.folder, f)):
                                 full_path = os.path.join(self.folder, f, "name.txt")
                                 name = open(full_path).read().strip()
                                 version = open(os.path.join(self.folder, f,
                                                             "version.txt")).read().strip()
-                                result[f"{name}/{version}"] = {"path": f}
+                                result.append({"path": f, "ref": f"{name}/{version}"})
                         return result
                 """)
         else:
@@ -154,11 +156,11 @@ def packages(self):

                 class MyWorkspace(Workspace):
                     def packages(self):
-                        result = {}
+                        result = []
                         for f in os.listdir(self.folder):
                             if os.path.isdir(os.path.join(self.folder, f)):
                                 conanfile = self.load_conanfile(f)
-                                result[f"{conanfile.name}/{conanfile.version}"] = {"path": f}
+                                result.append({"path": f, "ref": f"{conanfile.name}/{conanfile.version}"})
                         return result
                """)

@@ -168,12 +170,12 @@ def packages(self):
                 "dep1/version.txt": "2.1"})
         c.run("workspace info --format=json")
         info = json.loads(c.stdout)
-        assert info["packages"] == {"pkg/2.1": {"path": "dep1"}}
+        assert info["packages"] == [{"ref": "pkg/2.1", "path": "dep1"}]
         c.save({"dep1/name.txt": "other",
                 "dep1/version.txt": "14.5"})
         c.run("workspace info --format=json")
         info = json.loads(c.stdout)
-        assert info["packages"] == {"other/14.5": {"path": "dep1"}}
+        assert info["packages"] == [{"ref": "other/14.5", "path": "dep1"}]
         c.run("install --requires=other/14.5")
         # Doesn'"'"'t fail
         assert "other/14.5 - Editable" in c.out
@@ -203,14 +205,14 @@ def set_version(self):
             class MyWorkspace(Workspace):
                 def packages(self):
                     conanfile = self.load_conanfile("dep1")
-                    return {f"{conanfile.name}/{conanfile.version}": {"path": "dep1"}}
+                    return [{"path": "dep1", "ref": f"{conanfile.name}/{conanfile.version}"}]
             """)

         c.save({"conanws.py": workspace,
                 "dep1/conanfile.py": conanfile})
         c.run("workspace info --format=json")
         info = json.loads(c.stdout)
-        assert info["packages"] == {"pkg/2.1": {"path": "dep1"}}
+        assert info["packages"] == [{"ref": "pkg/2.1", "path": "dep1"}]
         c.run("install --requires=pkg/2.1")
         # it will not fail

@@ -250,7 +252,7 @@ def test_remove_removed_folder(self):
         shutil.rmtree(os.path.join(c.current_folder, "mydeppkg"))
         # It can still be removed by path, even if the path doesn'"'"'t exist
         c.run("workspace remove mydeppkg")
-        assert "Removed from workspace: mydeppkg/0.1" in c.out
+        assert "Removed from workspace: mydeppkg" in c.out
         c.run("workspace info")
         assert "mydeppkg" not in c.out

@@ -435,10 +437,10 @@ def build(self):

             class MyWorkspace(Workspace):
                 def packages(self):
-                    result = {}
+                    result = []
                     for f in os.listdir(self.folder):
                         if os.path.isdir(os.path.join(self.folder, f)):
-                            result[f"{f}/0.1"] = {"path": f}
+                            result.append({"path": f, "ref": f"{f}/0.1"})
                     return result
            """)
         c = TestClient(light=True)
@@ -642,12 +644,12 @@ def test_relative_paths():
         c.run("workspace add ../app1")
         c.run("workspace info")
         expected = textwrap.dedent("""\
-            packages
-              app1/0.1
-                path: ../app1
-              liba/0.1
-                path: ../liba
-            """)
+        packages
+          - path: ../liba
+            ref: liba/0.1
+          - path: ../app1
+            ref: app1/0.1
+        """)
         assert expected in c.out
         c.run("graph info --requires=app1/0.1")
         c.assert_listed_require({"app1/0.1": "Editable", "liba/0.1": "Editable"})
@@ -657,12 +659,12 @@ def test_relative_paths():
         c.run("workspace add ../other/app2")
         c.run("workspace info")
         expected = textwrap.dedent("""\
-            packages
-              app2/0.1
-                path: ../other/app2
-              libb/0.1
-                path: ../other/libb
-            """)
+        packages
+          - path: ../other/libb
+            ref: libb/0.1
+          - path: ../other/app2
+            ref: app2/0.1
+        """)
         assert expected in c.out
         c.run("graph info --requires=app2/0.1")
         c.assert_listed_require({"app2/0.1": "Editable", "libb/0.1": "Editable"})
@@ -787,10 +789,10 @@ def test_create_dynamic_name(self):

             class MyWorkspace(Workspace):
                 def packages(self):
-                    result = {}
+                    result = []
                     for f in os.listdir(self.folder):
                         if os.path.isdir(os.path.join(self.folder, f)):
-                            result[f"{f}/0.1"] = {"path": f}
+                            result.append({"path": f, "ref": f"{f}/0.1"})
                     return result
            """)
         c = TestClient(light=True)
@@ -934,3 +936,68 @@ def generate(self):
     c.save_home({"global.conf": "core:default_profile=myprofile"})
     c.run("workspace install")
     assert "conanfile.py (pkga/0.1): Generating!: FreeBSD-armv7!!!!" in c.out
+
+
+def test_workspace_defining_only_paths():
+    c = TestClient()
+    c.run("new workspace")
+    conanws_with_labels = textwrap.dedent("""\
+    packages:
+      - path: liba
+      - path: libb
+      - path: app1
+    """)
+    c.save({"conanws.yml": conanws_with_labels})
+    # liba with user and channel too
+    replace_in_file(ConanFileMock(), os.path.join(c.current_folder, "liba", "conanfile.py"),
+                    '"'"'version = "0.1"'"'"',
+                    '"'"'version = "0.1"\n    user = "myuser"\n    channel = "mychannel"'"'"')
+    replace_in_file(ConanFileMock(), os.path.join(c.current_folder, "libb", "conanfile.py"),
+                    '"'"'self.requires("liba/0.1")'"'"',
+                    '"'"'self.requires("liba/0.1@myuser/mychannel")'"'"')
+    c.run("workspace info")
+    expected = textwrap.dedent("""\
+    packages
+      - path: liba
+      - path: libb
+      - path: app1
+    """)
+    assert expected in c.out
+    c.run("workspace install")
+    assert "conanfile.py (app1/0.1)" in c.out
+    assert "liba/0.1@myuser/mychannel - Editable" in c.out
+    assert "libb/0.1 - Editable" in c.out
+
+
+def test_workspace_defining_duplicate_references():
+    """
+    Testing duplicate references but different paths
+    """
+    c = TestClient()
+    conanws_with_labels = textwrap.dedent("""\
+    packages:
+      - path: liba
+      - path: liba1
+      - path: liba2
+    """)
+    c.save({
+        "conanws.yml": conanws_with_labels,
+        "liba/conanfile.py": GenConanfile(name="liba", version="0.1"),
+        "liba1/conanfile.py": GenConanfile(name="liba", version="0.1"),
+        "liba2/conanfile.py": GenConanfile(name="liba", version="0.1"),
+    })
+    c.run("workspace install", assert_error=True)
+    assert "Workspace editable reference '"'"'liba/0.1'"'"' already exists." in c.out
+
+
+def test_workspace_reference_error():
+    c = TestClient()
+    conanws_with_labels = textwrap.dedent("""\
+    packages:
+      - path: libx
+    """)
+    c.save({"conanws.yml": conanws_with_labels,
+            "libx/conanfile.py": ""})
+    c.run("workspace install", assert_error=True)
+    assert ("Workspace editable reference could not be deduced by libx/conanfile.py or it is not"
+            " correctly defined in the conanws.yml file.") in c.out' > /tmp/test_patch.diff
        git apply --check /tmp/test_patch.diff
        git apply /tmp/test_patch.diff

        #Then we run all the tests in the repository
        #start recording terminal output in LOG_FILE
        LOG_FILE=$(mktemp)
        export LOG_FILE
        exec 3>&1 4>&2
        exec > >(tee "$LOG_FILE") 2>&1

        set +x
        python -m pytest -q -rA --tb=no -p no:pretty --timeout=1800 --continue-on-collection-errors --timeout-method=signal test/integration/workspace/test_workspace.py test/functional/command/config_install_test.py test/functional/command/export_test.py test/functional/command/profile_test.py test/functional/command/report_test.py test/functional/command/test_build.py test/functional/command/test_custom_symlink_home.py test/functional/command/test_install_deploy.py test/functional/command/test_new.py test/functional/layout/test_build_system_layout_helpers.py test/functional/layout/test_editable_cmake_components.py test/functional/layout/test_exports_sources.py test/functional/layout/test_in_cache.py test/functional/layout/test_in_subfolder.py test/functional/layout/test_layout_autopackage.py test/functional/layout/test_local_commands.py test/functional/layout/test_source_folder.py test/functional/only_source_test.py test/functional/revisions_test.py test/functional/sbom/test_cyclonedx.py test/functional/subsystems_build_test.py test/functional/test_local_recipes_index.py test/functional/test_profile_detect_api.py test/functional/test_third_party_patch_flow.py test/functional/toolchains/cmake/cmakedeps/test_build_context_protobuf.py test/functional/toolchains/cmake/cmakedeps/test_build_context_transitive_build.py test/functional/toolchains/cmake/cmakedeps/test_cmakedeps.py test/functional/toolchains/cmake/cmakedeps/test_cmakedeps_aggregator.py test/functional/toolchains/cmake/cmakedeps/test_cmakedeps_aliases.py test/functional/toolchains/cmake/cmakedeps/test_cmakedeps_and_linker_flags.py test/functional/toolchains/cmake/cmakedeps/test_cmakedeps_build_modules.py test/functional/toolchains/cmake/cmakedeps/test_cmakedeps_components.py test/functional/toolchains/cmake/cmakedeps/test_cmakedeps_components_names.py test/functional/toolchains/cmake/cmakedeps/test_cmakedeps_custom_configs.py test/functional/toolchains/cmake/cmakedeps/test_cmakedeps_find_module_and_config.py test/functional/toolchains/cmake/cmakedeps/test_cmakedeps_transitivity.py test/functional/toolchains/cmake/cmakedeps/test_cmakedeps_versions.py test/functional/toolchains/cmake/cmakedeps/test_conditional_build_type.py test/functional/toolchains/cmake/cmakedeps/test_weird_library_names.py test/functional/toolchains/cmake/cmakedeps2/test_cmakeconfigdeps_new.py test/functional/toolchains/cmake/cmakedeps2/test_cmakeconfigdeps_new_cpp_linkage.py test/functional/toolchains/cmake/cmakedeps2/test_cmakeconfigdeps_new_paths.py test/functional/toolchains/cmake/cmakedeps2/test_cmakeconfigdeps_sources.py test/functional/toolchains/cmake/test_cmake.py test/functional/toolchains/cmake/test_cmake_toolchain.py test/functional/toolchains/cmake/test_cmaketoolchain_paths.py test/functional/toolchains/cmake/test_shared_cmake.py test/functional/toolchains/cmake/test_transitive_build_scripts.py test/functional/toolchains/cmake/test_v2_cmake_template.py test/functional/toolchains/env/test_complete.py test/functional/toolchains/env/test_virtualenv_powershell.py test/functional/toolchains/gnu/autotools/test_basic.py test/functional/toolchains/gnu/test_makedeps.py test/functional/toolchains/gnu/test_pkg_config.py test/functional/toolchains/gnu/test_pkgconfigdeps.py test/functional/toolchains/microsoft/test_msbuilddeps.py test/functional/toolchains/qbs/test_qbsprofile_gen.py test/functional/toolchains/test_basic.py test/functional/toolchains/test_txt_cmdline.py test/functional/tools/scm/test_git.py test/functional/tools/scm/test_git_get_commit.py test/functional/tools/scm/test_version.py test/functional/tools/system/package_manager_test.py test/functional/tools/test_files.py test/functional/tools_versions_test.py test/functional/util/test_cmd_args_to_string.py test/functional/workspace/test_workspace.py test/integration/build_requires/build_requires_test.py test/integration/build_requires/profile_build_requires_test.py test/integration/build_requires/test_build_requires_source_method.py test/integration/build_requires/test_install_test_build_require.py test/integration/build_requires/test_relocatable_toolchain.py test/integration/build_requires/test_toolchain_packages.py test/integration/cache/backup_sources_test.py test/integration/cache/cache2_update_test.py test/integration/cache/download_cache_test.py test/integration/cache/storage_path_test.py test/integration/cache/test_home_special_char.py test/integration/cache/test_package_revisions.py test/integration/cache/test_same_pref_removal.py test/integration/command/alias_test.py test/integration/command/cache/test_cache_clean.py test/integration/command/cache/test_cache_integrity.py test/integration/command/cache/test_cache_path.py test/integration/command/cache/test_cache_save_restore.py test/integration/command/config_test.py test/integration/command/create_test.py test/integration/command/custom_commands_test.py test/integration/command/download/download_parallel_test.py test/integration/command/download/download_selected_packages_test.py test/integration/command/download/download_test.py test/integration/command/download/test_download_patterns.py test/integration/command/export/export_dirty_test.py test/integration/command/export/export_path_test.py test/integration/command/export/export_test.py test/integration/command/export/exports_method_test.py test/integration/command/export/test_export.py test/integration/command/export_pkg_test.py test/integration/command/help_test.py test/integration/command/info/info_options_test.py test/integration/command/info/info_test.py test/integration/command/info/test_graph_info_graphical.py test/integration/command/info/test_info_build_order.py test/integration/command/info/test_info_folders.py test/integration/command/install/install_missing_dep_test.py test/integration/command/install/install_test.py test/integration/command/install/install_update_test.py test/integration/command/install/test_graph_build_mode.py test/integration/command/install/test_install_transitive.py test/integration/command/list/list_test.py test/integration/command/list/search_test.py test/integration/command/list/test_combined_pkglist_flows.py test/integration/command/list/test_list_lru.py test/integration/command/remote_test.py test/integration/command/remote_verify_ssl_test.py test/integration/command/remove_empty_dirs_test.py test/integration/command/remove_test.py test/integration/command/source_test.py test/integration/command/test_audit.py test/integration/command/test_build.py test/integration/command/test_forced_download_source.py test/integration/command/test_graph_find_binaries.py test/integration/command/test_inspect.py test/integration/command/test_new.py test/integration/command/test_outdated.py test/integration/command/test_output.py test/integration/command/test_package_test.py test/integration/command/test_profile.py test/integration/command/test_remote_users.py test/integration/command/test_version.py test/integration/command/upload/test_upload_bundle.py test/integration/command/upload/test_upload_parallel.py test/integration/command/upload/test_upload_patterns.py test/integration/command/upload/upload_complete_test.py test/integration/command/upload/upload_compression_test.py test/integration/command/upload/upload_test.py test/integration/conan_api/list_test.py test/integration/conan_api/search_test.py test/integration/conan_api/test_cli.py test/integration/conan_api/test_local_api.py test/integration/conan_api/test_profile_api.py test/integration/conan_v2/test_legacy_cpp_info.py test/integration/conanfile/conan_data_test.py test/integration/conanfile/conanfile_errors_test.py test/integration/conanfile/conanfile_helpers_test.py test/integration/conanfile/folders_access_test.py test/integration/conanfile/generators_list_test.py test/integration/conanfile/init_test.py test/integration/conanfile/invalid_configuration_test.py test/integration/conanfile/load_requires_file_test.py test/integration/conanfile/no_copy_source_test.py test/integration/conanfile/required_conan_version_test.py test/integration/conanfile/runner_test.py test/integration/conanfile/same_userchannel_test.py test/integration/conanfile/set_name_version_test.py test/integration/conanfile/test_attributes_scope.py test/integration/conanfile/test_conanfile_txt_encodings.py test/integration/conanfile/test_conanfile_txt_test_requires.py test/integration/conanfile/test_cpp_info_serialize.py test/integration/conanfile/test_deploy_method.py test/integration/conanfile/test_deprecated.py test/integration/conanfile/test_exception_printing.py test/integration/conanfile/test_finalize_method.py test/integration/conanfile/test_print_in_conanfile.py test/integration/conanfile/test_version_str.py test/integration/configuration/client_certs_test.py test/integration/configuration/conf/test_auth_source_plugin.py test/integration/configuration/conf/test_conf.py test/integration/configuration/conf/test_conf_copy.py test/integration/configuration/conf/test_conf_from_br.py test/integration/configuration/conf/test_conf_package_id.py test/integration/configuration/conf/test_conf_profile.py test/integration/configuration/custom_setting_test_package_test.py test/integration/configuration/default_profile_test.py test/integration/configuration/invalid_settings_test.py test/integration/configuration/profile_test.py test/integration/configuration/proxies_conf_test.py test/integration/configuration/requester_test.py test/integration/configuration/required_version_test.py test/integration/configuration/test_auth_remote_plugin.py test/integration/configuration/test_custom_symlinked_home.py test/integration/configuration/test_profile_jinja.py test/integration/configuration/test_profile_plugin.py test/integration/configuration/test_profile_priority.py test/integration/cps/test_cps.py test/integration/cross_building/build_requires_from_profile_test.py test/integration/cross_building/test_cross_build_options.py test/integration/cross_building/test_package_test.py test/integration/editable/editable_add_test.py test/integration/editable/editable_remove_test.py test/integration/editable/forbidden_commands_test.py test/integration/editable/test_editable_envvars.py test/integration/editable/test_editable_import.py test/integration/editable/test_editable_layout.py test/integration/editable/test_editable_ranges.py test/integration/editable/test_editables_layout.py test/integration/editable/transitive_editable_test.py test/integration/environment/test_buildenv_profile.py test/integration/environment/test_env.py test/integration/environment/test_runenv_profile.py test/integration/export_sources_test.py test/integration/extensions/hooks/hook_test.py test/integration/extensions/hooks/test_post_export.py test/integration/extensions/hooks/test_post_package.py test/integration/extensions/test_cppstd_compat.py test/integration/extensions/test_plugin_cmd_wrapper.py test/integration/extensions/test_profile_plugin.py test/integration/generators/generators_test.py test/integration/generators/order_libs_test.py test/integration/generators/test_custom_global_generators.py test/integration/generators/test_generators_from_br.py test/integration/graph/conflict_diamond_test.py test/integration/graph/core/graph_manager_test.py test/integration/graph/core/test_alias.py test/integration/graph/core/test_auto_package_type.py test/integration/graph/core/test_build_require_invalid.py test/integration/graph/core/test_build_requires.py test/integration/graph/core/test_options.py test/integration/graph/core/test_provides.py test/integration/graph/core/test_version_ranges.py test/integration/graph/require_override_test.py test/integration/graph/test_dependencies_visit.py test/integration/graph/test_divergent_cppstd_build_host.py test/integration/graph/test_platform_requires.py test/integration/graph/test_pure_runtime_dep.py test/integration/graph/test_remote_resolution.py test/integration/graph/test_repackaging.py test/integration/graph/test_replace_requires.py test/integration/graph/test_require_same_pkg_versions.py test/integration/graph/test_skip_binaries.py test/integration/graph/test_skip_build.py test/integration/graph/test_subgraph_reports.py test/integration/graph/test_system_tools.py test/integration/graph/test_test_requires.py test/integration/graph/test_validate_build.py test/integration/graph/ux/loop_detection_test.py test/integration/graph/version_ranges/test_version_range_conf.py test/integration/graph/version_ranges/version_range_override_test.py test/integration/graph/version_ranges/version_ranges_cached_test.py test/integration/graph/version_ranges/version_ranges_diamond_test.py test/integration/layout/devflow_test.py test/integration/layout/export_folder_variable_test.py test/integration/layout/test_cmake_build_folder.py test/integration/layout/test_layout_generate.py test/integration/layout/test_layout_paths.py test/integration/layout/test_legacy_cpp_info_and_layout.py test/integration/lockfile/test_ci.py test/integration/lockfile/test_ci_overrides.py test/integration/lockfile/test_ci_revisions.py test/integration/lockfile/test_graph_overrides.py test/integration/lockfile/test_lock_alias.py test/integration/lockfile/test_lock_build_requires.py test/integration/lockfile/test_lock_merge.py test/integration/lockfile/test_lock_packages.py test/integration/lockfile/test_lock_pyrequires.py test/integration/lockfile/test_lock_pyrequires_revisions.py test/integration/lockfile/test_lock_requires.py test/integration/lockfile/test_lock_requires_revisions.py test/integration/lockfile/test_options.py test/integration/lockfile/test_user_overrides.py test/integration/metadata/test_metadata_collect.py test/integration/metadata/test_metadata_commands.py test/integration/metadata/test_metadata_deploy.py test/integration/metadata/test_metadata_logs.py test/integration/metadata/test_metadata_test_package.py test/integration/options/options_test.py test/integration/options/test_configure_options.py test/integration/options/test_options_build_requires.py test/integration/options/test_package_config_test.py test/integration/package_id/build_id_test.py test/integration/package_id/compatible_test.py test/integration/package_id/package_id_and_confs_test.py test/integration/package_id/package_id_modes_test.py test/integration/package_id/package_id_requires_modes_test.py test/integration/package_id/package_id_test.py test/integration/package_id/python_requires_package_id_test.py test/integration/package_id/test_cache_compatibles.py test/integration/package_id/test_config_package_id.py test/integration/package_id/test_default_package_id.py test/integration/package_id/test_package_id_test_requires.py test/integration/package_id/test_valid_package_id_values.py test/integration/package_id/test_validate.py test/integration/package_id/transitive_header_only_test.py test/integration/package_id/transitive_options_affect_id_test.py test/integration/py_requires/python_requires_test.py test/integration/remote/auth_bearer_test.py test/integration/remote/auth_test.py test/integration/remote/broken_download_test.py test/integration/remote/download_retries_test.py test/integration/remote/download_test.py test/integration/remote/multi_remote_checks_test.py test/integration/remote/multi_remote_test.py test/integration/remote/requester_test.py test/integration/remote/rest_api_test.py test/integration/remote/retry_test.py test/integration/remote/selected_remotes_test.py test/integration/remote/server_error_test.py test/integration/remote/test_conaninfo_parsing.py test/integration/remote/test_local_recipes_index.py test/integration/remote/test_offline.py test/integration/remote/test_remote_file_credentials.py test/integration/remote/test_request_headers.py test/integration/settings/built_type_setting_test.py test/integration/settings/per_package_settings_test.py test/integration/settings/remove_subsetting_test.py test/integration/settings/settings_override_test.py test/integration/settings/test_disable_settings_assignment.py test/integration/settings/test_non_defining_settings.py test/integration/settings/test_settings_possible_values.py test/integration/settings/test_settings_user.py test/integration/symlinks/symlinks_test.py test/integration/sysroot_test.py test/integration/system_reqs_test.py test/integration/test_components.py test/integration/test_components_error.py test/integration/test_db_error.py test/integration/test_migrations.py test/integration/test_package_python_files.py test/integration/test_package_vendor.py test/integration/test_pkg_signing.py test/integration/test_source_download_password.py test/integration/test_timestamp_error.py test/integration/toolchains/apple/test_xcodedeps.py test/integration/toolchains/apple/test_xcodetoolchain.py test/integration/toolchains/cmake/cmakedeps/test_cmakedeps.py test/integration/toolchains/cmake/cmakedeps/test_cmakedeps_find_module_and_config.py test/integration/toolchains/cmake/cmakedeps2/test_cmakedeps.py test/integration/toolchains/cmake/test_cmake.py test/integration/toolchains/cmake/test_cmaketoolchain.py test/integration/toolchains/cmake/test_cmaketoolchain_blocks.py test/integration/toolchains/env/test_environment.py test/integration/toolchains/env/test_virtualenv_default_apply.py test/integration/toolchains/env/test_virtualenv_object_access.py test/integration/toolchains/gnu/test_autotoolsdeps.py test/integration/toolchains/gnu/test_autotoolstoolchain.py test/integration/toolchains/gnu/test_basic_layout.py test/integration/toolchains/gnu/test_gnutoolchain.py test/integration/toolchains/gnu/test_makedeps.py test/integration/toolchains/gnu/test_pkgconfigdeps.py test/integration/toolchains/google/test_bazeldeps.py test/integration/toolchains/google/test_bazeltoolchain.py test/integration/toolchains/intel/test_intel_cc.py test/integration/toolchains/meson/test_mesontoolchain.py test/integration/toolchains/microsoft/test_msbuilddeps.py test/integration/toolchains/microsoft/test_msbuildtoolchain.py test/integration/toolchains/microsoft/test_vs_layout.py test/integration/toolchains/microsoft/vcvars_test.py test/integration/toolchains/premake/test_premake.py test/integration/toolchains/premake/test_premakedeps.py test/integration/toolchains/qbs/test_qbsdeps.py test/integration/toolchains/scons/test_scondeps.py test/integration/toolchains/test_raise_on_universal_binaries.py test/integration/toolchains/test_toolchain_namespaces.py test/integration/tools/conan_version_test.py test/integration/tools/cppstd_minimum_version_test.py test/integration/tools/cpu_count_test.py test/integration/tools/file_tools_test.py test/integration/tools/fix_symlinks_test.py test/integration/tools/ros/test_rosenv.py test/integration/tools/system/package_manager_test.py test/integration/ui/exit_with_code_test.py test/unittests/cli/common_test.py test/unittests/cli/test_cli_ref_matching.py test/unittests/client/build/c_std_flags_test.py test/unittests/client/build/compiler_flags_test.py test/unittests/client/build/cpp_std_flags_test.py test/unittests/client/command/parse_arguments_test.py test/unittests/client/conan_output_test.py test/unittests/client/conanfile_loader_test.py test/unittests/client/conf/config_installer/test_install_folder.py test/unittests/client/conf/detect/test_gcc_compiler.py test/unittests/client/file_copier/test_report_copied_files.py test/unittests/client/graph/build_mode_test.py test/unittests/client/graph/deps_graph_test.py test/unittests/client/optimize_conanfile_load_test.py test/unittests/client/profile_loader/compiler_cppstd_test.py test/unittests/client/profile_loader/profile_loader_test.py test/unittests/client/remote_manager_test.py test/unittests/client/rest/downloader_test.py test/unittests/client/rest/response_test.py test/unittests/client/rest/rest_client_v2/rest_client_v2_test.py test/unittests/client/rest/uploader_test.py test/unittests/client/toolchain/autotools/autotools_test.py test/unittests/client/toolchain/autotools/autotools_toolchain_test.py test/unittests/client/tools/apple/test_xcodebuild.py test/unittests/client/tools/cppstd_required_test.py test/unittests/client/tools/files/rename_test.py test/unittests/client/tools/test_env.py test/unittests/client/userio_test.py test/unittests/client/util/time_test.py test/unittests/model/build_info/components_test.py test/unittests/model/build_info/generic_properties_test.py test/unittests/model/build_info/new_build_info_test.py test/unittests/model/build_info/test_deduce_locations.py test/unittests/model/conanfile_test.py test/unittests/model/info_test.py test/unittests/model/manifest_test.py test/unittests/model/options_test.py test/unittests/model/other_settings_test.py test/unittests/model/profile_test.py test/unittests/model/settings_test.py test/unittests/model/test_conf.py test/unittests/model/test_package_reference.py test/unittests/model/test_recipe_reference.py test/unittests/model/version/test_version_bump.py test/unittests/model/version/test_version_comparison.py test/unittests/model/version/test_version_parse.py test/unittests/model/version/test_version_range.py test/unittests/model/version/test_version_range_intersection.py test/unittests/model/versionrepr_test.py test/unittests/paths/user_home_test.py test/unittests/search/search_query_parse_test.py test/unittests/server/authenticator_plugin_test.py test/unittests/server/conan_server_config_parser_test.py test/unittests/server/conf_test.py test/unittests/server/crypto/jwt_test.py test/unittests/server/revision_list_test.py test/unittests/server/service/authorizer_test.py test/unittests/server/service/service_test.py test/unittests/server/test_utils.py test/unittests/source/merge_directories_test.py test/unittests/tools/android/test_android_tools.py test/unittests/tools/apple/test_apple_tools.py test/unittests/tools/build/test_can_run.py test/unittests/tools/build/test_cppstd.py test/unittests/tools/build/test_cross_building.py test/unittests/tools/build/test_cstd.py test/unittests/tools/build/test_stdcpp_library.py test/unittests/tools/cmake/test_cmake_cmd_line_args.py test/unittests/tools/cmake/test_cmake_install.py test/unittests/tools/cmake/test_cmake_presets_definitions.py test/unittests/tools/cmake/test_cmake_test.py test/unittests/tools/cmake/test_cmaketoolchain.py test/unittests/tools/env/test_env.py test/unittests/tools/env/test_env_files.py test/unittests/tools/files/checksums_test.py test/unittests/tools/files/collect_lib_test.py test/unittests/tools/files/test_chmod.py test/unittests/tools/files/test_downloads.py test/unittests/tools/files/test_file_read_and_write.py test/unittests/tools/files/test_patches.py test/unittests/tools/files/test_rename.py test/unittests/tools/files/test_rm.py test/unittests/tools/files/test_symlinks.py test/unittests/tools/files/test_tool_copy.py test/unittests/tools/files/test_toolchain.py test/unittests/tools/files/test_zipping.py test/unittests/tools/files_patch_test.py test/unittests/tools/gnu/autotools_test.py test/unittests/tools/gnu/autotoolschain_test.py test/unittests/tools/gnu/gnudepsflags_test.py test/unittests/tools/gnu/test_gnutoolchain.py test/unittests/tools/gnu/test_triplets.py test/unittests/tools/google/test_bazel.py test/unittests/tools/intel/test_intel_cc.py test/unittests/tools/meson/test_meson.py test/unittests/tools/microsoft/test_check_min_vs.py test/unittests/tools/microsoft/test_msbuild.py test/unittests/tools/microsoft/test_msvs_toolset.py test/unittests/tools/microsoft/test_subsystem.py test/unittests/util/apple_test.py test/unittests/util/conanfile_tools_test.py test/unittests/util/detect_libc_test.py test/unittests/util/detect_test.py test/unittests/util/detected_architecture_test.py test/unittests/util/file_hashes_test.py test/unittests/util/files/strip_root_extract_test.py test/unittests/util/files/tar_extract_test.py test/unittests/util/files/test_copy_compat.py test/unittests/util/files/test_dirty.py test/unittests/util/files/test_remove.py test/unittests/util/files_extract_wildcard_test.py test/unittests/util/local_db_test.py test/unittests/util/output_test.py test/unittests/util/test_encrypt.py test/unittests/util/tools_test.py test/unittests/util/unix_path_test.py test/unittests/util/xz_test.py test/unittests/util/zip_permissions_test.py || true
        exec 1>&3 2>&4 # stop record
        exec 1>&3 2>&4 # stop record
        # And we reset the test files back to the base commit.
        git checkout ff5c4ffcefa632e11474221b014b23b0c9a3de22 test/integration/workspace/test_workspace.py
        # Remove only untracked files the FeatBench test patch touches.
for path in test/integration/workspace/test_workspace.py; do
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
