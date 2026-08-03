#!/usr/bin/env python3
"""Codeup and Flow CLI adapter for consolidated Yunxiao Bug delivery."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yunxiao_cli_bug_batch as core


PLAN_SCHEMA = "oneos.yunxiao-cli-bug-delivery-plan/v1"
PREFLIGHT_SCHEMA = "oneos.yunxiao-cli-bug-delivery-preflight/v1"
BRANCH_SCHEMA = "oneos.yunxiao-cli-bug-delivery-branches/v1"
MR_SCHEMA = "oneos.yunxiao-cli-bug-delivery-mrs/v1"
MERGE_SCHEMA = "oneos.yunxiao-cli-bug-delivery-merges/v1"
RUN_SCHEMA = "oneos.yunxiao-cli-bug-delivery-run/v1"
DEPLOYMENT_SCHEMA = "oneos.test-deployment/v1"
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
FORBIDDEN_BRANCH_RE = re.compile(r"[\s~^:?*\[\\\]]")
SENSITIVE_KEY_RE = re.compile(
    r"(?i)(access[_-]?token|token|secret|password|credential|signature|access[_-]?key)"
)
SUCCESS = {"SUCCESS", "SUCCEEDED", "PASSED"}
RUNNING = {"RUNNING", "WAITING", "PENDING", "QUEUED"}


def stable_hash(value: dict[str, Any]) -> str:
    clean = {key: item for key, item in value.items() if key not in {"hash", "receiptPath"}}
    raw = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise core.AdapterError(f"JSON文件必须是对象：{path}")
    return value


def load_receipt(path: str, schema: str) -> dict[str, Any]:
    value = load_json(path)
    if value.get("schema") != schema:
        raise core.AdapterError(f"回执格式不受支持：{path}")
    expected = value.get("hash")
    if not expected or expected != stable_hash(value):
        raise core.AdapterError(f"回执哈希不一致：{path}")
    return value


def write_receipt(path: Path, value: dict[str, Any]) -> None:
    value["hash"] = stable_hash(value)
    core.write_json(path, value)


def default_path(prefix: str, suffix: str) -> Path:
    return core.output_dir() / f"{prefix}-{suffix}.json"


def ensure_current_user(executable: str, expected: dict[str, Any] | None = None) -> dict[str, Any]:
    core.require_auth_env()
    user = core.current_user(executable)
    if expected and str(expected.get("id")) != str(user.get("id")):
        raise core.AdapterError("当前PAT用户与上一步回执用户不一致。")
    return user


def rows(value: Any, operation: str) -> list[dict[str, Any]]:
    payload = core.unwrap(value)
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise core.AdapterError(f"{operation}返回结构异常。")
    return [item for item in payload if isinstance(item, dict)]


def repository(executable: str, repository_id: str) -> dict[str, Any]:
    value = core.unwrap(core.run_devops(executable, [
        "codeup-get-repository", "--repository-id", repository_id,
    ]))
    if not isinstance(value, dict) or str(value.get("id")) != str(repository_id):
        raise core.AdapterError(f"Codeup代码库回读不一致：{repository_id}")
    if value.get("archived") is True:
        raise core.AdapterError(f"Codeup代码库已归档：{repository_id}")
    access = int(value.get("accessLevel") or 0)
    if access < 30:
        raise core.AdapterError(f"Codeup代码库写权限不足：{repository_id} accessLevel={access}")
    return value


def list_branches(executable: str, repository_id: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for page in range(1, 101):
        page_rows = rows(core.run_devops(executable, [
            "codeup-list-branches", "--repository-id", repository_id,
            "--page", str(page), "--per-page", "100",
        ]), "Codeup分支查询")
        result.extend(page_rows)
        if len(page_rows) < 100:
            break
    return result


def exact_branch(executable: str, repository_id: str, name: str) -> dict[str, Any] | None:
    matches = [item for item in list_branches(executable, repository_id)
               if str(item.get("name")) == name]
    if len(matches) > 1:
        raise core.AdapterError(f"Codeup分支出现重复精确匹配：{repository_id}/{name}")
    return matches[0] if matches else None


def branch_commit(branch: dict[str, Any] | None) -> str | None:
    commit = branch.get("commit") if isinstance(branch, dict) else None
    return str(commit.get("id")) if isinstance(commit, dict) and commit.get("id") else None


def validate_branch_name(name: str) -> None:
    if (not name or name.startswith(("-", ".", "/")) or name.endswith((".", "/"))
            or ".." in name or "//" in name or "@{" in name
            or FORBIDDEN_BRANCH_RE.search(name)):
        raise core.AdapterError(f"分支名称不安全：{name}")


def validate_safe_params(value: Any, path: str = "params") -> None:
    """Reject secrets in plans; credentials belong in protected pipeline variables."""
    if isinstance(value, dict):
        for key, item in value.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                raise core.AdapterError(
                    f"流水线参数{path}.{key}疑似凭证；请改用Flow受保护变量。")
            validate_safe_params(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            validate_safe_params(item, f"{path}[{index}]")
    elif isinstance(value, str):
        if core.TOKEN_RE.search(value) or core.SEC_VALUE_RE.search(value):
            raise core.AdapterError(f"流水线参数{path}疑似包含凭证；请改用Flow受保护变量。")


def pipeline_sources(pipeline: dict[str, Any]) -> list[dict[str, Any]]:
    config = pipeline.get("pipelineConfig")
    source_rows = config.get("sources", []) if isinstance(config, dict) else []
    result: list[dict[str, Any]] = []
    for item in source_rows:
        data = item.get("data") if isinstance(item, dict) else None
        if not isinstance(data, dict):
            continue
        result.append({
            "repo": str(data.get("repo") or ""),
            "label": str(data.get("label") or item.get("label") or ""),
            "branch": str(data.get("branch") or data.get("triggerFilter") or ""),
            "events": [str(event) for event in data.get("events") or []],
        })
    return result


def latest_pipeline_run_id(executable: str, pipeline_id: str) -> str | None:
    run_rows = rows(core.run_devops(executable, [
        "flow-list-pipeline-runs", "--pipeline-id", pipeline_id,
        "--page", "1", "--per-page", "1",
    ]), "Flow运行实例查询")
    return str(run_rows[0].get("pipelineRunId")) if run_rows and run_rows[0].get("pipelineRunId") else None


def validate_pipeline(executable: str, pipeline_spec: dict[str, Any],
                      groups: list[dict[str, Any]]) -> dict[str, Any]:
    pipeline_id = str(pipeline_spec.get("pipelineId") or "")
    expected_name = str(pipeline_spec.get("expectedName") or pipeline_spec.get("name") or "")
    environment = str(pipeline_spec.get("environment") or "").lower()
    execution_mode = str(pipeline_spec.get("executionMode") or "")
    params = pipeline_spec.get("params") or {}
    if not isinstance(params, dict):
        raise core.AdapterError("test流水线params必须是JSON对象。")
    validate_safe_params(params)
    if (not pipeline_id or not expected_name or environment != "test"
            or execution_mode not in {"manual-cli", "auto-after-merge"}):
        raise core.AdapterError(
            "test流水线计划必须包含pipelineId、expectedName（兼容name）、environment=test，"
            "并明确executionMode=manual-cli|auto-after-merge。")
    value = core.unwrap(core.run_devops(executable, [
        "flow-get-pipeline", "--pipeline-id", pipeline_id,
    ]))
    if not isinstance(value, dict) or str(value.get("id")) != pipeline_id:
        raise core.AdapterError("Flow流水线ID回读不一致。")
    actual_name = str(value.get("name") or "")
    lowered = actual_name.lower()
    if actual_name != expected_name or re.search(r"(^|[-_ ])prod(uction)?($|[-_ ])|生产", lowered):
        raise core.AdapterError(f"流水线不是精确预期的test流水线：{actual_name}")
    if not re.search(r"(^|[-_ ])test($|[-_ ])|测试", lowered):
        raise core.AdapterError(f"流水线名称缺少test环境标识：{actual_name}")
    sources = pipeline_sources(value)
    matched_sources: list[dict[str, Any]] = []
    for group in groups:
        repo_markers = {str(group.get("httpUrl") or ""), str(group.get("pathWithNamespace") or "")}
        target = str(group["targetBranch"])
        matched = [source for source in sources
                   if target == source.get("branch")
                   and any(marker and marker in {source.get("repo"), source.get("label")}
                           for marker in repo_markers)]
        if len(matched) != 1:
            raise core.AdapterError(
                f"流水线{pipeline_id}不能唯一覆盖提交组{group['groupId']}的代码库和目标分支。")
        matched_sources.extend(matched)
    relevant_events = sorted({event for source in matched_sources for event in source.get("events", [])
                              if event in {"merge_request/merged", "push"}})
    if execution_mode == "manual-cli" and relevant_events:
        raise core.AdapterError(
            "流水线已配置目标分支自动触发，不能再使用manual-cli，否则会重复发布。")
    if execution_mode == "auto-after-merge" and len(relevant_events) != 1:
        raise core.AdapterError(
            "auto-after-merge要求目标分支恰好一个自动触发事件；当前为："
            + ",".join(relevant_events))
    baseline = pipeline_spec.get("baselineLatestRunId")
    if baseline is None:
        baseline = latest_pipeline_run_id(executable, pipeline_id)
    return {"pipelineId": pipeline_id, "name": actual_name,
            "environment": "test", "sources": sources,
            "executionMode": execution_mode, "automaticEvents": relevant_events,
            "baselineLatestRunId": baseline, "params": params}


def load_plan(path: str, executable: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    plan = load_json(path)
    if plan.get("schema") != PLAN_SCHEMA:
        raise core.AdapterError("交付计划格式不受支持。")
    validate_safe_params(plan, "plan")
    snapshot_path = str(plan.get("snapshotPath") or "")
    snapshot = core.load_snapshot(snapshot_path)
    user = ensure_current_user(executable, snapshot.get("currentUser") or {})
    snapshot_bugs = {str(item.get("serialNumber")): item for item in snapshot.get("bugs", [])
                     if isinstance(item, dict) and item.get("serialNumber")}
    groups = plan.get("groups")
    if not isinstance(groups, list) or not groups:
        raise core.AdapterError("交付计划至少需要一个提交组。")
    group_ids: set[str] = set()
    assigned: set[str] = set()
    for group in groups:
        if not isinstance(group, dict):
            raise core.AdapterError("提交组必须是JSON对象。")
        group_id = str(group.get("groupId") or "")
        repository_id = str(group.get("repositoryId") or "")
        source = str(group.get("sourceBranch") or "")
        target = str(group.get("targetBranch") or "")
        bug_serials = [str(item) for item in group.get("bugSerials") or []]
        if not group_id or group_id in group_ids or not repository_id.isdigit():
            raise core.AdapterError("提交组ID必须唯一，repositoryId必须是Codeup数字ID。")
        validate_branch_name(source)
        validate_branch_name(target)
        if source == target or not bug_serials:
            raise core.AdapterError(f"提交组{group_id}的源/目标分支或Bug清单无效。")
        unknown = [item for item in bug_serials if item not in snapshot_bugs]
        duplicate = [item for item in bug_serials if item in assigned]
        if unknown or duplicate:
            raise core.AdapterError(f"提交组{group_id}包含快照外或重复Bug：{unknown + duplicate}")
        group_ids.add(group_id)
        assigned.update(bug_serials)
    return plan, snapshot, user


def cmd_preflight(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    plan, snapshot, user = load_plan(args.plan, executable)
    checked: list[dict[str, Any]] = []
    for spec in plan["groups"]:
        repo = repository(executable, str(spec["repositoryId"]))
        target = exact_branch(executable, str(spec["repositoryId"]), str(spec["targetBranch"]))
        source = exact_branch(executable, str(spec["repositoryId"]), str(spec["sourceBranch"]))
        if not target or not branch_commit(target):
            raise core.AdapterError(f"目标分支不存在或无提交：{spec['groupId']}")
        expected_source = spec.get("expectedSourceCommit")
        if source and not spec.get("reuseExisting", False):
            raise core.AdapterError(f"源分支已存在但计划未授权复用：{spec['groupId']}")
        if source and expected_source and branch_commit(source) != str(expected_source):
            raise core.AdapterError(f"源分支提交与计划不一致：{spec['groupId']}")
        checked.append({
            "groupId": str(spec["groupId"]), "repositoryId": str(repo["id"]),
            "repositoryName": repo.get("name"), "pathWithNamespace": repo.get("pathWithNamespace"),
            "httpUrl": repo.get("httpUrlToRepo"), "sourceBranch": str(spec["sourceBranch"]),
            "targetBranch": str(spec["targetBranch"]), "targetCommit": branch_commit(target),
            "sourceExisted": bool(source), "sourceCommit": branch_commit(source),
            "reuseExisting": bool(spec.get("reuseExisting", False)),
            "bugSerials": [str(item) for item in spec["bugSerials"]],
            "mrTitle": str(spec.get("mrTitle") or ""),
            "mrDescription": str(spec.get("mrDescription") or ""),
        })
    pipeline = validate_pipeline(executable, plan.get("testPipeline") or {}, checked)
    receipt = {
        "schema": PREFLIGHT_SCHEMA, "createdAt": core.now_utc(), "user": user,
        "planPath": str(Path(args.plan)), "planHash": stable_hash(plan),
        "snapshotPath": str(plan["snapshotPath"]), "snapshotHash": snapshot.get("snapshotHash"),
        "groups": checked, "testPipeline": pipeline,
    }
    suffix = str(snapshot.get("snapshotHash"))[:12]
    path = Path(args.output) if args.output else default_path("bug-delivery-preflight", suffix)
    write_receipt(path, receipt)
    print(json.dumps({"schema": PREFLIGHT_SCHEMA, "receiptPath": str(path),
                      "hash": receipt["hash"], "groups": checked,
                      "testPipeline": pipeline}, ensure_ascii=False, indent=2))
    return 0


def cmd_ensure_branches(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    preflight = load_receipt(args.preflight, PREFLIGHT_SCHEMA)
    user = ensure_current_user(executable, preflight.get("user"))
    results: list[dict[str, Any]] = []
    for group in preflight["groups"]:
        try:
            repo_id = str(group["repositoryId"])
            repository(executable, repo_id)
            target = exact_branch(executable, repo_id, str(group["targetBranch"]))
            if not target or branch_commit(target) != group.get("targetCommit"):
                raise core.AdapterError("目标分支在预检后发生变化，需重新预检。")
            source = exact_branch(executable, repo_id, str(group["sourceBranch"]))
            result = "idempotent"
            if source:
                if not group.get("sourceExisted") and branch_commit(source) != group.get("targetCommit"):
                    raise core.AdapterError("同名源分支在预检后被其他提交占用。")
                if group.get("sourceExisted") and not group.get("reuseExisting"):
                    raise core.AdapterError("计划未授权复用已有源分支。")
                if group.get("sourceExisted") and branch_commit(source) != group.get("sourceCommit"):
                    raise core.AdapterError("已有源分支在预检后发生变化，需重新预检。")
            else:
                core.run_devops(executable, [
                    "codeup-create-branch", "--repository-id", repo_id,
                    "--branch", str(group["sourceBranch"]), "--ref", str(group["targetBranch"]),
                ])
                source = exact_branch(executable, repo_id, str(group["sourceBranch"]))
                result = "created"
            if not source or not branch_commit(source):
                raise core.AdapterError("源分支创建/复用后回读失败。")
            results.append({**group, "result": result, "sourceCommit": branch_commit(source)})
        except core.AdapterError as exc:
            results.append({"groupId": group.get("groupId"), "result": "blocked", "error": str(exc)})
    receipt = {"schema": BRANCH_SCHEMA, "createdAt": core.now_utc(), "user": user,
               "preflightPath": str(Path(args.preflight)), "preflightHash": preflight.get("hash"),
               "snapshotPath": preflight.get("snapshotPath"),
               "snapshotHash": preflight.get("snapshotHash"),
               "testPipeline": preflight.get("testPipeline"), "results": results}
    suffix = str(preflight.get("snapshotHash"))[:12]
    path = Path(args.output) if args.output else default_path("bug-delivery-branches", suffix)
    write_receipt(path, receipt)
    print(json.dumps({**receipt, "receiptPath": str(path)}, ensure_ascii=False, indent=2))
    return 2 if any(item.get("result") == "blocked" for item in results) else 0


def list_mrs(executable: str, repository_id: str, state: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for page in range(1, 101):
        page_rows = rows(core.run_devops(executable, [
            "codeup-list-change-requests", "--project-ids", repository_id,
            "--state", state, "--page", str(page), "--per-page", "100",
        ]), "Codeup合并请求查询")
        result.extend(page_rows)
        if len(page_rows) < 100:
            break
    return result


def mr_detail(executable: str, repository_id: str, local_id: int) -> dict[str, Any]:
    value = core.unwrap(core.run_devops(executable, [
        "codeup-get-change-request", "--repository-id", repository_id,
        "--local-id", str(local_id),
    ]))
    if not isinstance(value, dict) or int(value.get("localId") or 0) != local_id:
        raise core.AdapterError("合并请求回读不一致。")
    return value


def mr_state(detail: dict[str, Any]) -> str:
    return str(detail.get("state") or detail.get("status") or "").upper()


def mr_can_merge(state: str) -> bool:
    return state.upper() in {"OPEN", "OPENED", "TO_BE_MERGED"}


def validate_mr(detail: dict[str, Any], group: dict[str, Any]) -> None:
    if (str(detail.get("projectId")) != str(group["repositoryId"])
            or str(detail.get("sourceBranch")) != str(group["sourceBranch"])
            or str(detail.get("targetBranch")) != str(group["targetBranch"])):
        raise core.AdapterError("合并请求代码库或分支回读不一致。")
    conflict_status = str(detail.get("conflictCheckStatus") or "").upper()
    if (detail.get("hasConflict") is True or detail.get("workInProgress") is True
            or conflict_status not in {"", "NO_CONFLICT"}):
        raise core.AdapterError("合并请求存在冲突或仍是WIP。")


def cmd_ensure_mrs(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    branches = load_receipt(args.branches, BRANCH_SCHEMA)
    user = ensure_current_user(executable, branches.get("user"))
    commits = load_json(args.commit_map)
    results: list[dict[str, Any]] = []
    for group in branches["results"]:
        try:
            if group.get("result") == "blocked":
                raise core.AdapterError("分支阶段已阻塞。")
            group_id = str(group["groupId"])
            expected_commit = str(commits.get(group_id) or "")
            if not COMMIT_RE.fullmatch(expected_commit):
                raise core.AdapterError("缺少本地推送后的40位远端提交ID。")
            repo_id = str(group["repositoryId"])
            source = exact_branch(executable, repo_id, str(group["sourceBranch"]))
            if branch_commit(source) != expected_commit:
                raise core.AdapterError("Codeup源分支提交与本地提交映射不一致。")
            title = str(group.get("mrTitle") or "")
            opened = [item for item in list_mrs(executable, repo_id, "opened")
                      if str(item.get("sourceBranch")) == str(group["sourceBranch"])
                      and str(item.get("targetBranch")) == str(group["targetBranch"])]
            if len(opened) > 1:
                raise core.AdapterError("存在多个相同源/目标分支的打开合并请求。")
            result = "idempotent"
            if opened:
                validate_mr(opened[0], group)
                local_id = int(opened[0].get("localId") or 0)
            else:
                merged = [item for item in list_mrs(executable, repo_id, "merged")
                          if str(item.get("sourceBranch")) == str(group["sourceBranch"])
                          and str(item.get("targetBranch")) == str(group["targetBranch"])
                          and (not title or str(item.get("title") or "") == title)]
                if len(merged) > 1:
                    raise core.AdapterError("存在多个与当前提交相同的已合并请求，无法唯一续跑。")
                if merged:
                    validate_mr(merged[0], group)
                    local_id = int(merged[0].get("localId") or 0)
                    result = "idempotent-merged"
                else:
                    if not title:
                        raise core.AdapterError("缺少合并请求标题。")
                    snapshot = core.load_snapshot(str(branches["snapshotPath"]))
                    by_serial = {str(item.get("serialNumber")): str(item.get("id"))
                                 for item in snapshot.get("bugs", []) if isinstance(item, dict)}
                    work_ids = [by_serial[item] for item in group["bugSerials"] if item in by_serial]
                    payload = core.unwrap(core.run_devops(executable, [
                        "codeup-create-change-request", "--repository-id", repo_id,
                        "--source-project-id", repo_id, "--source-branch", str(group["sourceBranch"]),
                        "--target-project-id", repo_id, "--target-branch", str(group["targetBranch"]),
                        "--title", title, "--description", str(group.get("mrDescription") or ""),
                        "--work-item-ids", ",".join(work_ids),
                    ]))
                    if not isinstance(payload, dict) or not payload.get("localId"):
                        raise core.AdapterError("创建合并请求后未返回localId。")
                    local_id = int(payload["localId"])
                    result = "created"
            detail = mr_detail(executable, repo_id, local_id)
            validate_mr(detail, group)
            results.append({**group, "result": result, "expectedSourceCommit": expected_commit,
                            "localId": local_id, "state": mr_state(detail),
                            "detailUrl": detail.get("detailUrl"), "hasConflict": detail.get("hasConflict")})
        except (core.AdapterError, KeyError, ValueError) as exc:
            results.append({"groupId": group.get("groupId"), "result": "blocked", "error": str(exc)})
    receipt = {"schema": MR_SCHEMA, "createdAt": core.now_utc(), "user": user,
               "branchesPath": str(Path(args.branches)), "branchesHash": branches.get("hash"),
               "snapshotPath": branches.get("snapshotPath"),
               "snapshotHash": branches.get("snapshotHash"),
               "testPipeline": branches.get("testPipeline"), "results": results}
    suffix = str(branches.get("snapshotHash"))[:12]
    path = Path(args.output) if args.output else default_path("bug-delivery-mrs", suffix)
    write_receipt(path, receipt)
    print(json.dumps({**receipt, "receiptPath": str(path)}, ensure_ascii=False, indent=2))
    return 2 if any(item.get("result") == "blocked" for item in results) else 0


def cmd_merge_mrs(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    mrs = load_receipt(args.mrs, MR_SCHEMA)
    user = ensure_current_user(executable, mrs.get("user"))
    results: list[dict[str, Any]] = []
    for group in mrs["results"]:
        try:
            if group.get("result") == "blocked":
                raise core.AdapterError("合并请求创建阶段已阻塞。")
            repo_id = str(group["repositoryId"])
            local_id = int(group["localId"])
            detail = mr_detail(executable, repo_id, local_id)
            validate_mr(detail, group)
            state = mr_state(detail)
            result = "idempotent"
            if state != "MERGED":
                if not mr_can_merge(state):
                    raise core.AdapterError(f"合并请求状态不允许合并：{state}")
                core.run_devops(executable, [
                    "codeup-merge-change-request", "--repository-id", repo_id,
                    "--local-id", str(local_id), "--merge-type", args.merge_type,
                    "--remove-source-branch", "false",
                ])
                detail = mr_detail(executable, repo_id, local_id)
                validate_mr(detail, group)
                result = "merged"
            if mr_state(detail) != "MERGED" or not detail.get("mergedRevision"):
                raise core.AdapterError("合并请求合并后状态或mergedRevision回读失败。")
            results.append({**group, "result": result, "state": "MERGED",
                            "mergedRevision": str(detail["mergedRevision"]),
                            "detailUrl": detail.get("detailUrl")})
        except (core.AdapterError, KeyError, ValueError) as exc:
            results.append({"groupId": group.get("groupId"), "result": "blocked", "error": str(exc)})
    receipt = {"schema": MERGE_SCHEMA, "createdAt": core.now_utc(), "user": user,
               "mrsPath": str(Path(args.mrs)), "mrsHash": mrs.get("hash"),
               "snapshotPath": mrs.get("snapshotPath"), "snapshotHash": mrs.get("snapshotHash"),
               "testPipeline": mrs.get("testPipeline"), "results": results}
    suffix = str(mrs.get("snapshotHash"))[:12]
    path = Path(args.output) if args.output else default_path("bug-delivery-merges", suffix)
    write_receipt(path, receipt)
    print(json.dumps({**receipt, "receiptPath": str(path)}, ensure_ascii=False, indent=2))
    return 2 if any(item.get("result") == "blocked" for item in results) else 0


def extract_run_id(payload: Any) -> str:
    value = core.unwrap(payload)
    if isinstance(value, (str, int)):
        return str(value)
    if isinstance(value, dict):
        for key in ("pipelineRunId", "runId", "id"):
            if value.get(key) is not None:
                return str(value[key])
    raise core.AdapterError("启动流水线后未返回pipelineRunId。")


def cmd_start_test(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    merges = load_receipt(args.merges, MERGE_SCHEMA)
    user = ensure_current_user(executable, merges.get("user"))
    blocked = [item for item in merges["results"] if item.get("result") == "blocked"]
    if blocked:
        raise core.AdapterError("存在未合并提交组，禁止触发test流水线。")
    pipeline = validate_pipeline(executable, merges["testPipeline"], merges["results"])
    for group in merges["results"]:
        target = exact_branch(executable, str(group["repositoryId"]), str(group["targetBranch"]))
        if branch_commit(target) != str(group["mergedRevision"]):
            raise core.AdapterError(f"目标分支未精确指向已合并版本：{group['groupId']}")
    suffix = f"{str(merges.get('snapshotHash'))[:12]}-{pipeline['pipelineId']}"
    path = Path(args.output) if args.output else default_path("bug-delivery-run", suffix)
    if path.exists():
        existing = load_receipt(str(path), RUN_SCHEMA)
        if existing.get("mergesHash") != merges.get("hash"):
            raise core.AdapterError("流水线回执文件已存在但不属于当前合并批次。")
        print(json.dumps({**existing, "receiptPath": str(path), "result": "idempotent"},
                         ensure_ascii=False, indent=2))
        return 0
    mode = str(pipeline.get("executionMode") or "")
    result = "started"
    if mode == "manual-cli":
        command = ["flow-create-pipeline-run", "--pipeline-id", str(pipeline["pipelineId"])]
        if pipeline.get("params"):
            command.extend(["--params", json.dumps(pipeline["params"], ensure_ascii=False,
                                                    separators=(",", ":"))])
        run_id = extract_run_id(core.run_devops(executable, command, timeout=120))
    elif mode == "auto-after-merge":
        expected = {str(item["mergedRevision"]).lower() for item in merges["results"]}
        baseline_text = str(pipeline.get("baselineLatestRunId") or "0")
        baseline = int(baseline_text) if baseline_text.isdigit() else 0
        candidates = rows(core.run_devops(executable, [
            "flow-list-pipeline-runs", "--pipeline-id", str(pipeline["pipelineId"]),
            "--page", "1", "--per-page", "30",
        ]), "Flow自动运行实例查询")
        matched_run_ids: list[str] = []
        for candidate in candidates:
            candidate_id = str(candidate.get("pipelineRunId") or "")
            if not candidate_id.isdigit() or int(candidate_id) <= baseline:
                continue
            detail = core.unwrap(core.run_devops(executable, [
                "flow-get-pipeline-run", "--pipeline-id", str(pipeline["pipelineId"]),
                "--pipeline-run-id", candidate_id,
            ], timeout=120))
            actual = collect_commit_ids({"sources": detail.get("sources") if isinstance(detail, dict) else None,
                                         "globalParams": detail.get("globalParams") if isinstance(detail, dict) else None})
            if expected.issubset(actual):
                matched_run_ids.append(candidate_id)
        if not matched_run_ids:
            print(json.dumps({"schema": RUN_SCHEMA, "result": "waiting-for-auto-trigger",
                              "pipelineId": pipeline["pipelineId"],
                              "baselineLatestRunId": pipeline.get("baselineLatestRunId")},
                             ensure_ascii=False, indent=2))
            return 3
        if len(matched_run_ids) != 1:
            raise core.AdapterError(
                "合并后检测到多个包含同一修复版本的test流水线实例，违反单次发布约束："
                + ",".join(matched_run_ids))
        run_id = matched_run_ids[0]
        result = "attached-auto-run"
    else:
        raise core.AdapterError("流水线执行模式无效，需重新预检。")
    receipt = {"schema": RUN_SCHEMA, "createdAt": core.now_utc(), "user": user,
               "mergesPath": str(Path(args.merges)), "mergesHash": merges.get("hash"),
               "snapshotPath": merges.get("snapshotPath"), "snapshotHash": merges.get("snapshotHash"),
               "pipeline": pipeline, "pipelineRunId": run_id, "groups": merges["results"]}
    write_receipt(path, receipt)
    print(json.dumps({**receipt, "receiptPath": str(path), "result": result},
                     ensure_ascii=False, indent=2))
    return 0


def collect_commit_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"secretKey", "params", "result", "pipelineConfig"}:
                continue
            found.update(collect_commit_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(collect_commit_ids(item))
    elif isinstance(value, str):
        found.update(match.lower() for match in re.findall(r"\b[0-9a-fA-F]{40}\b", value))
        if value[:1] in {"[", "{"}:
            try:
                found.update(collect_commit_ids(json.loads(value)))
            except json.JSONDecodeError:
                pass
    return found


def collect_pipeline_commit_ids(detail: dict[str, Any]) -> set[str]:
    """只从可信版本字段和作业触发参数中提取流水线提交版本。"""
    found = collect_commit_ids({
        "sources": detail.get("sources"),
        "globalParams": detail.get("globalParams"),
    })
    trusted_keys = {
        "commitid", "commit_id", "revision", "sha", "sourceversion",
        "source_version", "targetcommitid", "target_commit_id",
    }

    def visit(value: Any, trusted: bool = False) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = str(key).replace("-", "_").lower()
                visit(item, trusted or normalized in trusted_keys)
        elif isinstance(value, list):
            for item in value:
                visit(item, trusted)
        elif isinstance(value, str):
            if trusted:
                found.update(match.lower() for match in COMMIT_RE.findall(value))
            if value[:1] in {"[", "{"}:
                try:
                    visit(json.loads(value), trusted)
                except json.JSONDecodeError:
                    pass

    visit(detail.get("stages"))
    return found


def cmd_check_test(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    run = load_receipt(args.run, RUN_SCHEMA)
    ensure_current_user(executable, run.get("user"))
    pipeline_id = str((run.get("pipeline") or {}).get("pipelineId") or "")
    run_id = str(run.get("pipelineRunId") or "")
    detail = core.unwrap(core.run_devops(executable, [
        "flow-get-pipeline-run", "--pipeline-id", pipeline_id,
        "--pipeline-run-id", run_id,
    ], timeout=120))
    if not isinstance(detail, dict) or str(detail.get("pipelineRunId")) != run_id:
        raise core.AdapterError("流水线运行实例回读不一致。")
    status = str(detail.get("status") or "").upper()
    summary = {"schema": DEPLOYMENT_SCHEMA, "environment": "test",
               "pipelineId": pipeline_id, "pipelineRunId": run_id,
               "executionId": run_id, "pipelineName": (run.get("pipeline") or {}).get("name"),
               "status": status, "checkedAt": core.now_utc()}
    if status in RUNNING:
        print(json.dumps({**summary, "result": "running"}, ensure_ascii=False, indent=2))
        return 3
    if status not in SUCCESS:
        print(json.dumps({**summary, "result": "failed"}, ensure_ascii=False, indent=2))
        return 2
    actual_commits = collect_pipeline_commit_ids(detail)
    expected = {str(item["mergedRevision"]).lower() for item in run["groups"]}
    missing = sorted(expected - actual_commits)
    if missing:
        raise core.AdapterError("test流水线成功，但运行实例未证明包含全部合并版本：" + ",".join(missing))
    bugs = sorted({str(bug) for group in run["groups"] for bug in group.get("bugSerials", [])})
    anchors = [f"{item['repositoryId']}!{item['localId']}@{item['mergedRevision']}"
               for item in run["groups"]]
    evidence = {**summary, "status": "成功", "result": "success",
                "deployedVersion": ",".join(sorted(expected)),
                "includedBugSerials": bugs, "commitOrMrAnchors": anchors,
                "sourceCommits": sorted(actual_commits),
                "startTime": detail.get("createTime") or detail.get("startTime"),
                "endTime": detail.get("updateTime") or detail.get("endTime")}
    suffix = f"{str(run.get('snapshotHash'))[:12]}-{pipeline_id}-{run_id}"
    path = Path(args.output) if args.output else default_path("bug-delivery-evidence", suffix)
    core.write_json(path, evidence)
    print(json.dumps({**evidence, "evidencePath": str(path)}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Official Codeup/Flow CLI adapter for batch Bug delivery")
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight", help="只读校验提交组和唯一test流水线")
    preflight.add_argument("--plan", required=True)
    preflight.add_argument("--output")
    preflight.set_defaults(func=cmd_preflight)
    branches = sub.add_parser("ensure-branches", help="通过CLI创建或复用计划内Codeup分支")
    branches.add_argument("--preflight", required=True)
    branches.add_argument("--output")
    branches.set_defaults(func=cmd_ensure_branches)
    mrs = sub.add_parser("ensure-mrs", help="校验远端提交并通过CLI创建或复用MR")
    mrs.add_argument("--branches", required=True)
    mrs.add_argument("--commit-map", required=True)
    mrs.add_argument("--output")
    mrs.set_defaults(func=cmd_ensure_mrs)
    merge = sub.add_parser("merge-mrs", help="通过CLI合并精确MR并回读")
    merge.add_argument("--mrs", required=True)
    merge.add_argument("--merge-type", choices=("ff-only", "no-fast-forward", "squash", "rebase"),
                       default="no-fast-forward")
    merge.add_argument("--output")
    merge.set_defaults(func=cmd_merge_mrs)
    start = sub.add_parser("start-test-pipeline", help="通过CLI且仅一次启动预检test流水线")
    start.add_argument("--merges", required=True)
    start.add_argument("--output")
    start.set_defaults(func=cmd_start_test)
    check = sub.add_parser("check-test-pipeline", help="通过CLI查询运行并生成可核验部署证据")
    check.add_argument("--run", required=True)
    check.add_argument("--output")
    check.set_defaults(func=cmd_check_test)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (core.AdapterError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"result": "blocked", "error": core.scrub(str(exc))},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
