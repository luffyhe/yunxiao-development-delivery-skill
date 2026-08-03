import sys
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).parents[1] / "skills" / "yunxiao-development-delivery" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import yunxiao_cli_bug_batch as core  # noqa: E402
import yunxiao_cli_bug_delivery as delivery  # noqa: E402
import yunxiao_cli_allocate_task as allocation  # noqa: E402
import yunxiao_cli_gateway as gateway  # noqa: E402


class CliAdapterTests(unittest.TestCase):
    def setUp(self):
        self.groups = [{
            "groupId": "frontend-develop",
            "repositoryId": "6316668",
            "pathWithNamespace": "ln-one-os-web",
            "httpUrl": "https://codeup.example/org/ln-one-os-web.git",
            "targetBranch": "develop",
        }]

    @staticmethod
    def pipeline(events):
        return {
            "id": "4754190",
            "name": "oneos-web-test",
            "pipelineConfig": {
                "sources": [{
                    "label": "ln-one-os-web",
                    "data": {
                        "repo": "https://codeup.example/org/ln-one-os-web.git",
                        "branch": "develop",
                        "events": events,
                    },
                }],
            },
        }

    def test_scrub_removes_cli_and_webhook_secrets(self):
        raw = (
            "pt-" + ("x" * 32) + " "
            "access_token=abc123&signature=xyz secretKey: SECabcdefghijklmnop"
        )
        cleaned = core.scrub(raw)
        self.assertNotIn("x" * 32, cleaned)
        self.assertNotIn("abc123", cleaned)
        self.assertNotIn("xyz", cleaned)
        self.assertNotIn("SECabcdefghijklmnop", cleaned)
        self.assertIn("<redacted-token>", cleaned)
        self.assertGreaterEqual(cleaned.count("<redacted-secret>"), 3)

    def test_devops_json_is_parsed_before_output_scrubbing(self):
        payload = {"url": "https://example.test/hook?signature=keep-for-json"}
        completed = subprocess.CompletedProcess(
            args=["aliyun"], returncode=0, stdout=json.dumps(payload), stderr="")
        with patch.object(core.subprocess, "run", return_value=completed):
            self.assertEqual(core.run_devops("aliyun", ["base-get-user-by-token"]), payload)

    def test_gateway_requires_stable_idempotency_key(self):
        plan = {
            "schema": gateway.PLAN_SCHEMA,
            "authority": "apply",
            "guards": [{"operation": "projex-get-workitem", "args": ["--id", "1"]}],
            "actions": [{"operation": "projex-update-workitem", "args": ["--id", "1"]}],
            "verifications": [{"operation": "projex-get-workitem", "args": ["--id", "1"]}],
        }
        with self.assertRaises(gateway.core.AdapterError):
            gateway.validate_plan(plan)

    def test_gateway_rejects_unapproved_write_and_secret_args(self):
        with self.assertRaises(gateway.core.AdapterError):
            gateway.validate_call({"operation": "projex-delete-workitem", "args": []}, True)
        with self.assertRaises(gateway.core.AdapterError):
            gateway.validate_call({
                "operation": "flow-create-pipeline-run",
                "args": ["--access-token", "do-not-store"],
            }, True)
        with self.assertRaises(gateway.core.AdapterError):
            gateway.assert_no_secrets({"expect": {"secretKey": "do-not-store"}})

    def test_gateway_branch_delete_needs_cleanup_confirmation(self):
        plan = {
            "schema": gateway.PLAN_SCHEMA,
            "authority": "cleanup",
            "idempotencyKey": "cleanup-release-1-branch-a",
            "guards": [{"operation": "codeup-get-branch", "args": ["--repository-id", "1"]}],
            "actions": [{"operation": "codeup-delete-branch", "args": ["--repository-id", "1"]}],
            "verifications": [{"operation": "codeup-list-branches", "args": ["--repository-id", "1"]}],
        }
        with self.assertRaises(gateway.core.AdapterError):
            gateway.validate_plan(plan)
        plan["destructiveConfirmation"] = True
        self.assertEqual(gateway.validate_plan(plan)["authority"], "cleanup")

    def test_gateway_resolves_action_output_token(self):
        args = gateway.resolve_args(["--id", "${action.0.id}"], [{"result": {"id": "42"}}])
        self.assertEqual(args, ["--id", "42"])

    def test_normal_workitem_status_is_case_insensitive(self):
        self.assertTrue(core.is_normal_workitem({"logicalStatus": "NORMAL"}))
        self.assertTrue(core.is_normal_workitem({"logicalStatus": "normal"}))
        self.assertTrue(core.is_normal_workitem({}))
        self.assertFalse(core.is_normal_workitem({"logicalStatus": "ARCHIVED"}))

    def test_external_relations_query_every_supported_category(self):
        with patch.object(core, "safe_optional", return_value=([], None)) as optional:
            records, errors = core.load_external_relations("aliyun", "bug-id")
        self.assertEqual(records, [])
        self.assertEqual(errors, [])
        self.assertEqual(
            [call.args[1][-1] for call in optional.call_args_list],
            list(core.EXTERNAL_RELATION_CATEGORIES),
        )

    def test_allocation_owner_uses_user_id_not_membership_id(self):
        members = [{
            "id": "membership-id", "userId": "user-id", "name": "李振",
            "status": "ENABLED",
        }]
        with patch.object(core, "run_devops", return_value=members):
            self.assertEqual(
                allocation.resolve_owner("aliyun", "李振"),
                {"id": "user-id", "name": "李振"},
            )

    def test_allocation_managed_markdown_is_idempotent(self):
        original = "人工说明\n\n## 下一阶段\n/skill old\n/go old"
        once, format_type = allocation.managed_description(original, "MARKDOWN", "ONEOS-417")
        twice, _ = allocation.managed_description(once, format_type, "ONEOS-417")
        self.assertEqual(once, twice)
        self.assertIn("人工说明", once)
        self.assertEqual(once.count("## 下一阶段"), 1)
        self.assertIn("/go 开发任务:任务=ONEOS-417", once)

    def test_allocation_rejects_reversed_dates(self):
        with self.assertRaises(core.AdapterError):
            allocation.validate_dates("2026-08-05", "2026-08-03", "8")

    def test_allocation_serializes_integer_hours_as_decimal(self):
        self.assertEqual(allocation.decimal_field_value("16"), "16.0")
        self.assertEqual(allocation.decimal_field_value("16.50"), "16.50")

    def test_allocation_defers_hours_until_update(self):
        scope = {
            "delivery": {
                "id": "delivery-id", "subject": "【交付】示例",
                "priorityId": "priority-high",
            },
            "fieldIds": {
                "planStart": "start-field", "planFinish": "finish-field",
                "estimatedHours": "hours-field",
            },
            "input": {
                "planStart": "2026-08-03", "planFinish": "2026-08-07",
                "estimatedHours": "16.0",
            },
            "projectId": "project-id", "workitemTypeId": "type-id", "sprintId": None,
        }
        created = {
            "id": "development-id",
            "customFieldValues": [{
                "fieldId": "priority",
                "values": [{"identifier": "priority-high", "displayValue": "高"}],
            }],
        }
        with patch.object(core, "run_devops", return_value={"id": "development-id"}) as run, \
                patch.object(allocation, "get_workitem", return_value=created):
            allocation.create_development("aliyun", scope, "owner-id")
        args = run.call_args.args[1]
        custom = json.loads(args[args.index("--custom-field-values") + 1])
        self.assertNotIn("hours-field", custom)
        self.assertEqual(custom["priority"], "priority-high")

    def test_allocation_blocks_priority_readback_mismatch(self):
        scope = {
            "delivery": {
                "id": "delivery-id", "subject": "【交付】示例",
                "priorityId": "priority-high",
            },
            "fieldIds": {"planStart": "start-field", "planFinish": "finish-field"},
            "input": {"planStart": "2026-08-03", "planFinish": "2026-08-07"},
            "projectId": "project-id", "workitemTypeId": "type-id", "sprintId": None,
        }
        created = {
            "id": "development-id",
            "customFieldValues": [{
                "fieldId": "priority", "values": [{"identifier": "priority-low"}],
            }],
        }
        with patch.object(core, "run_devops", return_value={"id": "development-id"}), \
                patch.object(allocation, "get_workitem", return_value=created), \
                self.assertRaises(core.AdapterError):
            allocation.create_development("aliyun", scope, "owner-id")

    def test_allocation_creates_and_reads_back_estimated_effort(self):
        records = [
            [],
            [{"id": "estimate-id", "spentTime": 16, "owner": {"id": "owner-id"}}],
        ]
        with patch.object(allocation, "list_estimated_efforts", side_effect=records), \
                patch.object(core, "run_devops", return_value={"id": "estimate-id"}) as run:
            result = allocation.ensure_estimated_effort(
                "aliyun", "development-id", "owner-id", "16.0")
        self.assertEqual(result["result"], "created")
        self.assertEqual(result["estimatedHours"], "16.0")
        self.assertEqual(run.call_args.args[1][0], "projex-create-estimated-effort")

    def test_allocation_relation_creation_is_read_back(self):
        with patch.object(allocation, "relation_ids", side_effect=[[], ["parent-id"]]), \
                patch.object(core, "run_devops") as run:
            result = allocation.ensure_relation("aliyun", "child-id", "PARENT", "parent-id")
        self.assertEqual(result, "created")
        run.assert_called_once_with("aliyun", [
            "projex-create-workitem-relation-record", "--id", "child-id",
            "--relation-type", "PARENT", "--workitem-id", "parent-id",
        ])

    def test_auto_pipeline_accepts_one_event_and_preserves_baseline(self):
        spec = {
            "pipelineId": "4754190",
            "expectedName": "oneos-web-test",
            "environment": "test",
            "executionMode": "auto-after-merge",
            "baselineLatestRunId": "9001",
            "params": {},
        }
        with patch.object(core, "run_devops", return_value=self.pipeline(["push"])), \
                patch.object(delivery, "latest_pipeline_run_id") as latest:
            result = delivery.validate_pipeline("aliyun", spec, self.groups)
        self.assertEqual(result["automaticEvents"], ["push"])
        self.assertEqual(result["baselineLatestRunId"], "9001")
        latest.assert_not_called()

    def test_pipeline_name_alias_is_accepted(self):
        spec = {
            "pipelineId": "4754190",
            "name": "oneos-web-test",
            "environment": "test",
            "executionMode": "manual-cli",
            "params": {},
        }
        with patch.object(core, "run_devops", return_value=self.pipeline([])), \
                patch.object(delivery, "latest_pipeline_run_id", return_value="9001"):
            result = delivery.validate_pipeline("aliyun", spec, self.groups)
        self.assertEqual(result["name"], "oneos-web-test")

    def test_auto_pipeline_blocks_two_relevant_events(self):
        spec = {
            "pipelineId": "4754190",
            "expectedName": "oneos-web-test",
            "environment": "test",
            "executionMode": "auto-after-merge",
            "params": {},
        }
        with patch.object(core, "run_devops", return_value=self.pipeline([
                "push", "merge_request/merged"])), self.assertRaises(core.AdapterError):
            delivery.validate_pipeline("aliyun", spec, self.groups)

    def test_manual_pipeline_blocks_automatic_event(self):
        spec = {
            "pipelineId": "4754190",
            "expectedName": "oneos-web-test",
            "environment": "test",
            "executionMode": "manual-cli",
            "params": {},
        }
        with patch.object(core, "run_devops", return_value=self.pipeline(["push"])), \
                self.assertRaises(core.AdapterError):
            delivery.validate_pipeline("aliyun", spec, self.groups)

    def test_pipeline_plan_rejects_secret_parameters(self):
        spec = {
            "pipelineId": "4754190",
            "expectedName": "oneos-web-test",
            "environment": "test",
            "executionMode": "manual-cli",
            "params": {"accessToken": "do-not-store"},
        }
        with self.assertRaises(core.AdapterError):
            delivery.validate_pipeline("aliyun", spec, self.groups)

        spec["params"] = {"envs": {"releaseValue": "pt-secret-value-123456"}}
        with self.assertRaises(core.AdapterError):
            delivery.validate_pipeline("aliyun", spec, self.groups)

    def test_collect_commit_ids_ignores_untrusted_large_fields(self):
        commit = "0123456789abcdef0123456789abcdef01234567"
        ignored = "fedcba9876543210fedcba9876543210fedcba98"
        found = delivery.collect_commit_ids({
            "sources": [{"revision": commit}],
            "pipelineConfig": {"secretKey": ignored},
            "params": {"password": ignored},
        })
        self.assertEqual(found, {commit})

    def test_codeup_detail_status_is_normalized(self):
        self.assertEqual(delivery.mr_state({"status": "MERGED"}), "MERGED")
        self.assertEqual(delivery.mr_state({"state": "opened"}), "OPENED")

    def test_codeup_to_be_merged_status_can_merge(self):
        self.assertTrue(delivery.mr_can_merge("TO_BE_MERGED"))

    def test_pipeline_commit_is_read_from_nested_trigger_info(self):
        commit = "0123456789abcdef0123456789abcdef01234567"
        detail = {
            "stages": [{"jobs": [{"params": json.dumps({
                "triggerInfo": {"target_commit_id": commit},
            })}]}],
        }
        self.assertEqual(delivery.collect_pipeline_commit_ids(detail), {commit})

    def test_codeup_conflict_status_blocks_merge(self):
        group = {
            "repositoryId": "6316668",
            "sourceBranch": "fix/ONEOS-123",
            "targetBranch": "develop",
        }
        detail = {
            "projectId": 6316668,
            "sourceBranch": "fix/ONEOS-123",
            "targetBranch": "develop",
            "conflictCheckStatus": "CONFLICT",
        }
        with self.assertRaises(core.AdapterError):
            delivery.validate_mr(detail, group)


if __name__ == "__main__":
    unittest.main()
