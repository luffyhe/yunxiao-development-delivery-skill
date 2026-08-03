#!/usr/bin/env python3
"""Official aliyun devops CLI adapter for the consolidated Bug-repair command."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


SCHEMA = "oneos.yunxiao-cli-bug-batch/v1"
DEFAULT_ACTIONABLE = ("待确认", "待处理", "处理中", "再次打开", "重新打开")
TERMINAL_OR_QA = {"已修复", "已关闭", "已取消", "关闭", "取消", "待复测", "验证中"}
EXTERNAL_RELATION_CATEGORIES = (
    "codeupMergeRequest", "codeupBranch", "codeupCommit", "ChangeRequest",
)
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TOKEN_RE = re.compile(r"pt-[A-Za-z0-9_\-]+")
QUERY_SECRET_RE = re.compile(r"(?i)(access_token|token|signature)=([^&\s\"']+)")
NAMED_SECRET_RE = re.compile(
    r"(?im)^(\s*(?:secret|secretKey|password|credential)\s*[:=]\s*)(.+)$"
)
SEC_VALUE_RE = re.compile(r"\bSEC[A-Za-z0-9_\-]{16,}\b")
LOCK = threading.Lock()


class AdapterError(RuntimeError):
    pass


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def output_dir() -> Path:
    root = os.environ.get("ONEOS_YUNXIAO_TEMP_DIR")
    path = Path(root) if root else Path(tempfile.gettempdir()) / "oneos-yunxiao"
    path.mkdir(parents=True, exist_ok=True)
    return path


def scrub(text: str) -> str:
    token = os.environ.get("ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN", "")
    cleaned = ANSI_RE.sub("", text or "")
    if token:
        cleaned = cleaned.replace(token, "<redacted-token>")
    cleaned = TOKEN_RE.sub("<redacted-token>", cleaned)
    cleaned = QUERY_SECRET_RE.sub(lambda match: f"{match.group(1)}=<redacted-secret>", cleaned)
    cleaned = NAMED_SECRET_RE.sub(lambda match: f"{match.group(1)}<redacted-secret>", cleaned)
    return SEC_VALUE_RE.sub("<redacted-secret>", cleaned)


def find_aliyun() -> str:
    explicit = os.environ.get("ALIYUN_CLI_PATH")
    candidates = [explicit, shutil.which("aliyun")]
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.append(str(Path(local) / "AliyunCLI" / "aliyun.exe"))
    candidates.extend(("/usr/local/bin/aliyun", "/opt/homebrew/bin/aliyun"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    raise AdapterError("未找到aliyun CLI。请安装官方阿里云CLI并安装aliyun-cli-devops插件。")


def run_raw(executable: str, args: list[str], timeout: int = 90,
            scrub_output: bool = True) -> str:
    command = [executable, *args]
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": timeout,
        "env": os.environ.copy(),
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(command, **kwargs)
    raw_stdout = completed.stdout.strip()
    stdout = scrub(raw_stdout)
    stderr = scrub(completed.stderr).strip()
    if completed.returncode != 0:
        detail = stderr or stdout or f"exit={completed.returncode}"
        raise AdapterError(f"CLI调用失败：{' '.join(args[:2])}；{detail}")
    return stdout if scrub_output else raw_stdout


def run_devops(executable: str, args: list[str], timeout: int = 90) -> Any:
    text = run_raw(executable, ["devops", *args], timeout=timeout, scrub_output=False)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AdapterError(
            f"CLI返回的不是JSON：{' '.join(args[:1])}；{scrub(text[:500])}"
        ) from exc


def unwrap(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("result", "data"):
            if key in value and len(value) <= 4:
                return value[key]
    return value


def require_auth_env() -> dict[str, bool]:
    flags = {
        "token": bool(os.environ.get("ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN")),
        "organizationId": bool(os.environ.get("ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID")),
        "apiBaseUrl": bool(os.environ.get("ALIBABA_CLOUD_YUNXIAO_API_BASE_URL")),
    }
    if not flags["token"]:
        raise AdapterError("缺少ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN。请在本机安全设置PAT，不要通过聊天传递。")
    if not flags["organizationId"] and not flags["apiBaseUrl"]:
        raise AdapterError("中心版需设置ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID；Region版需设置ALIBABA_CLOUD_YUNXIAO_API_BASE_URL。")
    return flags


def current_user(executable: str) -> dict[str, Any]:
    value = unwrap(run_devops(executable, ["base-get-user-by-token"]))
    if not isinstance(value, dict) or not value.get("id"):
        raise AdapterError("PAT用户回读失败，未取得唯一用户ID。")
    return {"id": value.get("id"), "name": value.get("name") or value.get("nickName")}


def status_name(item: dict[str, Any]) -> str:
    status = item.get("status")
    if isinstance(status, dict):
        return str(status.get("displayName") or status.get("name") or "")
    return str(status or "")


def person_id(item: dict[str, Any], field: str) -> str | None:
    value = item.get(field)
    return str(value.get("id")) if isinstance(value, dict) and value.get("id") else None


def serial(item: dict[str, Any]) -> str:
    return str(item.get("serialNumber") or item.get("identifier") or "")


def is_normal_workitem(item: dict[str, Any]) -> bool:
    return str(item.get("logicalStatus") or "NORMAL").upper() == "NORMAL"


def search_assigned_bugs(executable: str, space_id: str, user_id: str) -> list[dict[str, Any]]:
    conditions = {
        "conditionGroups": [[{
            "fieldIdentifier": "assignedTo",
            "operator": "CONTAINS",
            "value": [user_id],
            "toValue": None,
            "className": "user",
            "format": "list",
        }]]
    }
    result: list[dict[str, Any]] = []
    page = 1
    while page <= 100:
        payload = unwrap(run_devops(executable, [
            "projex-search-workitems", "--category", "Bug", "--space-id", space_id,
            "--conditions", json.dumps(conditions, ensure_ascii=False, separators=(",", ":")),
            "--page", str(page), "--per-page", "200", "--sort", "asc",
        ]))
        if payload is None:
            rows: list[Any] = []
        elif isinstance(payload, list):
            rows = payload
        else:
            raise AdapterError(f"项目{space_id}的Bug查询返回结构异常。")
        result.extend(row for row in rows if isinstance(row, dict))
        if len(rows) < 200:
            break
        page += 1
    return result


def safe_optional(executable: str, args: list[str]) -> tuple[Any, str | None]:
    try:
        return unwrap(run_devops(executable, args)), None
    except AdapterError as exc:
        return None, str(exc)


def load_external_relations(executable: str, workitem_id: str) -> tuple[list[Any], list[str]]:
    records: list[Any] = []
    errors: list[str] = []
    for category in EXTERNAL_RELATION_CATEGORIES:
        value, error = safe_optional(executable, [
            "projex-list-workitem-ext-relation-records", "--id", workitem_id,
            "--category", category,
        ])
        if isinstance(value, list):
            records.extend(value)
        elif value is not None:
            records.append(value)
        if error:
            errors.append(f"{category}: {error}")
    return records, errors


def hydrate_bug(executable: str, row: dict[str, Any]) -> dict[str, Any]:
    workitem_id = str(row.get("id") or "")
    if not workitem_id:
        return {"summary": row, "detail": None, "relations": None, "externalRelations": None,
                "errors": ["缺少工作项内部ID"]}
    detail, detail_error = safe_optional(executable, ["projex-get-workitem", "--id", workitem_id])
    relations, relation_error = safe_optional(executable, [
        "projex-list-workitem-relation-records", "--id", workitem_id,
        "--relation-type", "ASSOCIATED",
    ])
    external, external_errors = load_external_relations(executable, workitem_id)
    errors = [e for e in (detail_error, relation_error) if e] + external_errors
    live = detail if isinstance(detail, dict) else row
    return {
        "id": workitem_id,
        "serialNumber": serial(live),
        "subject": live.get("subject"),
        "space": live.get("space") or row.get("space"),
        "sprint": live.get("sprint") or row.get("sprint"),
        "status": live.get("status") or row.get("status"),
        "assignedTo": live.get("assignedTo") or row.get("assignedTo"),
        "verifier": live.get("verifier") or row.get("verifier"),
        "logicalStatus": live.get("logicalStatus") or row.get("logicalStatus"),
        "workitemType": live.get("workitemType") or row.get("workitemType"),
        "description": live.get("description"),
        "relations": relations,
        "externalRelations": external,
        "errors": errors,
    }


def snapshot_hash(snapshot: dict[str, Any]) -> str:
    stable = {
        "currentUser": snapshot.get("currentUser"),
        "spaceIds": snapshot.get("spaceIds"),
        "bugs": [{
            "id": bug.get("id"), "serialNumber": bug.get("serialNumber"),
            "status": status_name(bug), "assignedTo": person_id(bug, "assignedTo"),
            "verifier": person_id(bug, "verifier"),
        } for bug in snapshot.get("bugs", [])],
    }
    encoded = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_doctor(args: argparse.Namespace) -> int:
    executable = find_aliyun()
    core = run_raw(executable, ["version"])
    plugin = run_raw(executable, ["devops", "version"])
    flags = {
        "token": bool(os.environ.get("ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN")),
        "organizationId": bool(os.environ.get("ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID")),
        "apiBaseUrl": bool(os.environ.get("ALIBABA_CLOUD_YUNXIAO_API_BASE_URL")),
    }
    user = None
    ready = flags["token"] and (flags["organizationId"] or flags["apiBaseUrl"])
    error = None
    if ready:
        try:
            user = current_user(executable)
        except AdapterError as exc:
            ready, error = False, str(exc)
    elif args.require_auth:
        error = "缺少PAT以及中心版组织ID或Region版API接入点。"
    print(json.dumps({
        "schema": SCHEMA, "command": "doctor", "ready": ready,
        "cliPath": executable, "cliVersion": core, "pluginVersion": plugin,
        "credentialFlags": flags, "currentUser": user, "error": error,
    }, ensure_ascii=False, indent=2))
    return 0 if ready or not args.require_auth else 69


def cmd_snapshot(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    executable = find_aliyun()
    require_auth_env()
    user = current_user(executable)
    spaces = list(dict.fromkeys(args.space_id))
    if not spaces:
        raise AdapterError("至少需要一个精确--space-id；官方搜索接口不支持跨项目无界查询。")
    actionable = tuple(args.actionable_status or DEFAULT_ACTIONABLE)
    if TERMINAL_OR_QA.intersection(actionable):
        raise AdapterError("可处理状态不得包含已修复、关闭、取消或待复测状态。")
    rows: list[dict[str, Any]] = []
    for space_id in spaces:
        rows.extend(search_assigned_bugs(executable, space_id, str(user["id"])))
    unique = {str(row.get("id")): row for row in rows if row.get("id")}
    filtered = [row for row in unique.values()
                if is_normal_workitem(row)
                and status_name(row) in actionable
                and person_id(row, "assignedTo") == str(user["id"])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        hydrated = list(pool.map(lambda row: hydrate_bug(executable, row), filtered))
    hydrated = [bug for bug in hydrated
                if bug.get("serialNumber") and status_name(bug) in actionable
                and person_id(bug, "assignedTo") == str(user["id"])]
    hydrated.sort(key=lambda bug: (str((bug.get("space") or {}).get("name") or ""),
                                   str(bug.get("serialNumber") or "")))
    snapshot = {
        "schema": SCHEMA, "command": "snapshot", "createdAt": now_utc(),
        "currentUser": user, "spaceIds": spaces, "actionableStatuses": list(actionable),
        "bugs": hydrated,
    }
    snapshot["snapshotHash"] = snapshot_hash(snapshot)
    snapshot["durationMs"] = round((time.perf_counter() - started) * 1000)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(args.output) if args.output else output_dir() / f"bug-batch-snapshot-{stamp}.json"
    write_json(path, snapshot)
    print(json.dumps({
        "schema": SCHEMA, "command": "snapshot", "snapshotPath": str(path),
        "snapshotHash": snapshot["snapshotHash"], "currentUser": user,
        "spaceIds": spaces, "bugCount": len(hydrated), "durationMs": snapshot["durationMs"],
        "bugs": [{
            "serialNumber": bug.get("serialNumber"), "subject": bug.get("subject"),
            "status": status_name(bug), "owner": bug.get("assignedTo"),
            "verifier": bug.get("verifier"), "relationErrors": bug.get("errors"),
        } for bug in hydrated],
    }, ensure_ascii=False, indent=2))
    return 0


def load_snapshot(path: str) -> dict[str, Any]:
    snapshot = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        raise AdapterError("快照格式或版本不受支持。")
    expected = snapshot.get("snapshotHash")
    actual = snapshot_hash(snapshot)
    if not expected or expected != actual:
        raise AdapterError("快照哈希不一致，拒绝状态写入。")
    return snapshot


def validate_deployment(path: str, requested: set[str]) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AdapterError("test部署证据必须是JSON对象。")
    environment = str(data.get("environment") or data.get("env") or "").lower()
    status = str(data.get("status") or data.get("pipelineStatus") or "").lower()
    execution_id = data.get("executionId") or data.get("pipelineRunId")
    version = data.get("deployedVersion") or data.get("version") or data.get("artifact")
    anchors = data.get("commitOrMrAnchors") or data.get("includedCommits") or data.get("includedMrs")
    included = data.get("includedBugSerials") or data.get("bugs") or []
    if environment != "test" or status not in {"成功", "success", "succeeded", "passed"}:
        raise AdapterError("只有test环境终态成功证据才能标记已修复。")
    if not execution_id or not version or not anchors:
        raise AdapterError("test部署证据缺少执行ID、部署版本/制品或提交/MR锚点。")
    included_set = {str(value) for value in included}
    missing = sorted(requested - included_set)
    if missing:
        raise AdapterError(f"test部署证据未覆盖Bug：{','.join(missing)}")
    return {
        "environment": environment, "status": status, "executionId": execution_id,
        "executionUrl": data.get("executionUrl"), "version": version,
        "commitOrMrAnchors": anchors, "includedBugSerials": sorted(included_set),
    }


def resolve_target_status(executable: str, live: dict[str, Any], target: str,
                          cache: dict[tuple[str, str], str]) -> str:
    space = live.get("space") if isinstance(live.get("space"), dict) else {}
    item_type = live.get("workitemType") if isinstance(live.get("workitemType"), dict) else {}
    key = (str(space.get("id") or ""), str(item_type.get("id") or ""))
    if not all(key):
        raise AdapterError("工作项缺少项目ID或工作项类型ID，无法解析真实工作流。")
    with LOCK:
        if key in cache:
            return cache[key]
    workflow = unwrap(run_devops(executable, [
        "projex-get-workitem-workflow", "--project-id", key[0], "--id", key[1],
    ]))
    statuses = workflow.get("statuses", []) if isinstance(workflow, dict) else []
    matches = [str(row.get("id")) for row in statuses if isinstance(row, dict)
               and target in {str(row.get("name") or ""), str(row.get("displayName") or "")}
               and row.get("id")]
    if len(set(matches)) != 1:
        raise AdapterError(f"目标状态{target}在项目工作流中不是唯一匹配。")
    with LOCK:
        cache[key] = matches[0]
    return matches[0]


def update_one(executable: str, bug: dict[str, Any], user_id: str, target: str,
               workflow_cache: dict[tuple[str, str], str]) -> dict[str, Any]:
    workitem_id = str(bug.get("id") or "")
    expected_serial = str(bug.get("serialNumber") or "")
    before_owner = person_id(bug, "assignedTo")
    before_verifier = person_id(bug, "verifier")
    try:
        live = unwrap(run_devops(executable, ["projex-get-workitem", "--id", workitem_id]))
        if not isinstance(live, dict) or serial(live) != expected_serial:
            raise AdapterError("编号回读不一致。")
        if person_id(live, "assignedTo") != user_id or before_owner != user_id:
            raise AdapterError("负责人已变化或不再是当前PAT用户。")
        if person_id(live, "verifier") != before_verifier:
            raise AdapterError("验证者与冻结快照不一致。")
        before_status = status_name(live)
        if before_status == target:
            return {"serialNumber": expected_serial, "result": "idempotent",
                    "before": before_status, "after": before_status,
                    "ownerUnchanged": True, "verifierUnchanged": True}
        allowed = set(DEFAULT_ACTIONABLE)
        if before_status not in allowed:
            raise AdapterError(f"当前状态{before_status}不属于开发可处理状态。")
        target_id = resolve_target_status(executable, live, target, workflow_cache)
        body = json.dumps({"status": target_id}, ensure_ascii=False, separators=(",", ":"))
        run_devops(executable, ["projex-update-workitem", "--id", workitem_id,
                                "--biz-body", body])
        after = unwrap(run_devops(executable, ["projex-get-workitem", "--id", workitem_id]))
        if not isinstance(after, dict) or serial(after) != expected_serial or status_name(after) != target:
            raise AdapterError("状态写入后的编号或状态回读不一致。")
        if person_id(after, "assignedTo") != user_id:
            raise AdapterError("状态写入后负责人发生变化。")
        if person_id(after, "verifier") != before_verifier:
            raise AdapterError("状态写入后验证者发生变化。")
        return {"serialNumber": expected_serial, "result": "updated",
                "before": before_status, "after": status_name(after),
                "ownerUnchanged": True, "verifierUnchanged": True}
    except AdapterError as exc:
        return {"serialNumber": expected_serial, "result": "blocked", "error": str(exc)}


def cmd_set_status(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    executable = find_aliyun()
    require_auth_env()
    user = current_user(executable)
    snapshot = load_snapshot(args.snapshot)
    if str((snapshot.get("currentUser") or {}).get("id")) != str(user["id"]):
        raise AdapterError("当前PAT用户与冻结快照用户不一致。")
    requested = list(dict.fromkeys(args.serial or []))
    if not requested:
        raise AdapterError("状态写入必须显式提供至少一个--serial，禁止默认处理整个快照。")
    by_serial: dict[str, dict[str, Any]] = {}
    for bug in snapshot.get("bugs", []):
        if isinstance(bug, dict) and bug.get("serialNumber"):
            key = str(bug["serialNumber"])
            if key in by_serial:
                raise AdapterError(f"快照中Bug编号重复：{key}")
            by_serial[key] = bug
    missing = [value for value in requested if value not in by_serial]
    if missing:
        raise AdapterError(f"请求包含快照外Bug：{','.join(missing)}")
    deployment = None
    if args.target == "已修复":
        if not args.deployment_evidence:
            raise AdapterError("标记已修复必须提供--deployment-evidence。")
        deployment = validate_deployment(args.deployment_evidence, set(requested))
    elif args.deployment_evidence:
        raise AdapterError("只有目标为已修复时才接受部署证据。")
    workflow_cache: dict[tuple[str, str], str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(update_one, executable, by_serial[value], str(user["id"]),
                               args.target, workflow_cache) for value in requested]
        results = [future.result() for future in futures]
    receipt = {
        "schema": SCHEMA, "command": "set-status", "createdAt": now_utc(),
        "snapshotPath": str(Path(args.snapshot)), "snapshotHash": snapshot.get("snapshotHash"),
        "currentUser": user, "target": args.target, "deploymentEvidence": deployment,
        "results": results, "durationMs": round((time.perf_counter() - started) * 1000),
    }
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    receipt_path = Path(args.receipt) if args.receipt else output_dir() / f"bug-batch-status-{stamp}.json"
    write_json(receipt_path, receipt)
    blocked = [row for row in results if row.get("result") == "blocked"]
    print(json.dumps({**receipt, "receiptPath": str(receipt_path)}, ensure_ascii=False, indent=2))
    return 2 if blocked else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Official aliyun devops CLI adapter for batch Bug repair")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="检查CLI、插件和PAT配置")
    doctor.add_argument("--require-auth", action="store_true")
    doctor.set_defaults(func=cmd_doctor)
    snapshot = sub.add_parser("snapshot", help="冻结当前PAT用户负责的可处理Bug")
    snapshot.add_argument("--space-id", action="append", required=True)
    snapshot.add_argument("--actionable-status", action="append")
    snapshot.add_argument("--workers", type=int, default=6)
    snapshot.add_argument("--output")
    snapshot.set_defaults(func=cmd_snapshot)
    status = sub.add_parser("set-status", help="对冻结快照内显式Bug写状态并回读")
    status.add_argument("--snapshot", required=True)
    status.add_argument("--target", required=True, choices=("处理中", "已修复"))
    status.add_argument("--serial", action="append", required=True)
    status.add_argument("--deployment-evidence")
    status.add_argument("--workers", type=int, default=4)
    status.add_argument("--receipt")
    status.set_defaults(func=cmd_set_status)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (AdapterError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": SCHEMA, "result": "blocked", "error": scrub(str(exc))},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
