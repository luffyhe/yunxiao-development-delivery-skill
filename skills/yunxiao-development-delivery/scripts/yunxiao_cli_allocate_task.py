#!/usr/bin/env python3
"""Official aliyun devops CLI adapter for the 分配任务 command."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yunxiao_cli_bug_batch as core


SCHEMA = "oneos.yunxiao-cli-allocation/v1"
SERIAL_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)-(\d+)$")
MARKDOWN_BLOCK_RE = re.compile(r"(?ms)^## 下一阶段\s*\n.*?(?=^## |\Z)")
HTML_BLOCK_RE = re.compile(r"(?is)<h2>下一阶段</h2>.*?(?=<h2>|\Z)")


def canonical_hash(value: dict[str, Any], excluded: set[str] | None = None) -> str:
    filtered = {k: v for k, v in value.items() if k not in (excluded or set())}
    encoded = json.dumps(filtered, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def item_status(item: dict[str, Any]) -> str:
    return core.status_name(item)


def item_serial(item: dict[str, Any]) -> str:
    return core.serial(item)


def item_user_id(item: dict[str, Any]) -> str | None:
    return core.person_id(item, "assignedTo")


def list_projects(executable: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(1, 101):
        value = core.unwrap(core.run_devops(executable, [
            "projex-search-projects", "--page", str(page), "--per-page", "100",
        ]))
        if value is None:
            batch: list[Any] = []
        elif isinstance(value, list):
            batch = value
        else:
            raise core.AdapterError("项目查询返回结构异常。")
        rows.extend(row for row in batch if isinstance(row, dict))
        if len(batch) < 100:
            break
    return rows


def resolve_project(executable: str, task_serial: str,
                    explicit_space_id: str | None = None) -> dict[str, Any]:
    projects = [row for row in list_projects(executable)
                if str(row.get("logicalStatus") or "NORMAL").upper() == "NORMAL"]
    if explicit_space_id:
        matches = [row for row in projects if str(row.get("id")) == explicit_space_id]
    else:
        match = SERIAL_RE.fullmatch(task_serial)
        if not match:
            raise core.AdapterError("任务编号格式无效，无法解析项目代码。")
        code = match.group(1).upper()
        matches = [row for row in projects
                   if str(row.get("customCode") or "").upper() == code]
    if len(matches) != 1:
        raise core.AdapterError(f"任务{task_serial}无法解析到唯一项目。")
    return matches[0]


def search_workitems(executable: str, space_id: str, category: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(1, 101):
        value = core.unwrap(core.run_devops(executable, [
            "projex-search-workitems", "--category", category, "--space-id", space_id,
            "--page", str(page), "--per-page", "200", "--sort", "asc",
        ]))
        if value is None:
            batch: list[Any] = []
        elif isinstance(value, list):
            batch = value
        else:
            raise core.AdapterError(f"项目{space_id}的{category}查询返回结构异常。")
        rows.extend(row for row in batch if isinstance(row, dict))
        if len(batch) < 200:
            break
    return rows


def get_workitem(executable: str, workitem_id: str) -> dict[str, Any]:
    value = core.unwrap(core.run_devops(executable, [
        "projex-get-workitem", "--id", workitem_id,
    ]))
    if not isinstance(value, dict) or not value.get("id"):
        raise core.AdapterError(f"工作项{workitem_id}回读失败。")
    return value


def find_workitem_by_serial(executable: str, space_id: str, category: str,
                            serial_number: str) -> dict[str, Any]:
    matches = [row for row in search_workitems(executable, space_id, category)
               if item_serial(row) == serial_number and core.is_normal_workitem(row)]
    if len(matches) != 1:
        raise core.AdapterError(f"项目中未找到唯一工作项{serial_number}。")
    return get_workitem(executable, str(matches[0]["id"]))


def relation_ids(executable: str, workitem_id: str, relation_type: str) -> list[str]:
    value = core.unwrap(core.run_devops(executable, [
        "projex-list-workitem-relation-records", "--id", workitem_id,
        "--relation-type", relation_type,
    ]))
    if value is None:
        return []
    if not isinstance(value, list):
        raise core.AdapterError(f"工作项关系{relation_type}返回结构异常。")
    return sorted({str(row.get("resourceId")) for row in value
                   if isinstance(row, dict) and row.get("resourceId")})


def resolve_owner(executable: str, name: str) -> dict[str, Any] | None:
    value = core.unwrap(core.run_devops(executable, [
        "base-search-members", "--query", name, "--page", "1", "--per-page", "100",
    ]))
    rows = value if isinstance(value, list) else []
    matches = [row for row in rows if isinstance(row, dict)
               and str(row.get("name") or "") == name
               and str(row.get("status") or "ENABLED") in {"ENABLED", "NORMAL_USING", "UNVISITED"}
               and (row.get("userId") or row.get("id"))]
    user_ids = {str(row.get("userId") or row.get("id")) for row in matches}
    if len(user_ids) != 1:
        return None
    row = matches[0]
    return {"id": next(iter(user_ids)), "name": row.get("name")}


def workitem_type_fields(executable: str, project_id: str,
                         type_id: str) -> list[dict[str, Any]]:
    value = core.unwrap(core.run_devops(executable, [
        "projex-get-workitem-type-field-config", "--project-id", project_id,
        "--id", type_id,
    ]))
    if not isinstance(value, list):
        raise core.AdapterError("任务字段配置返回结构异常。")
    return [row for row in value if isinstance(row, dict)]


def unique_field_id(fields: list[dict[str, Any]], name: str, expected_format: str) -> str:
    matches = [str(row.get("id")) for row in fields
               if row.get("id") and str(row.get("name") or "") == name
               and str(row.get("format") or "").lower() == expected_format.lower()]
    if len(set(matches)) != 1:
        raise core.AdapterError(f"任务字段{name}无法唯一解析。")
    return matches[0]


def workflow_status_id(executable: str, project_id: str, type_id: str,
                       name: str) -> str:
    value = core.unwrap(core.run_devops(executable, [
        "projex-get-workitem-workflow", "--project-id", project_id, "--id", type_id,
    ]))
    statuses = value.get("statuses", []) if isinstance(value, dict) else []
    matches = [str(row.get("id")) for row in statuses if isinstance(row, dict)
               and row.get("id") and name in {
                   str(row.get("name") or ""), str(row.get("displayName") or "")
               }]
    if len(set(matches)) != 1:
        raise core.AdapterError(f"任务状态{name}无法唯一解析。")
    return matches[0]


def managed_description(current: str | None, format_type: str | None,
                        development_serial: str) -> tuple[str, str]:
    command = f"/go 开发任务:任务={development_serial}"
    if str(format_type or "").upper() == "RICHTEXT":
        block = ("<h2>下一阶段</h2><p>/skill yunxiao-development-delivery</p>"
                 f"<p>{command}</p>")
        source = current or ""
        updated = (HTML_BLOCK_RE.sub(block, source, count=1)
                   if HTML_BLOCK_RE.search(source) else f"{source}{block}")
        return updated, "RICHTEXT"
    block = ("## 下一阶段\n/skill yunxiao-development-delivery\n"
             f"{command}\n")
    source = current or ""
    updated = (MARKDOWN_BLOCK_RE.sub(block.rstrip(), source, count=1)
               if MARKDOWN_BLOCK_RE.search(source)
               else (f"{source.rstrip()}\n\n{block}" if source.strip() else block))
    return updated.rstrip(), "MARKDOWN"


def field_value(item: dict[str, Any], field_id: str) -> str | None:
    for row in item.get("customFieldValues") or []:
        if isinstance(row, dict) and str(row.get("fieldId")) == field_id:
            values = row.get("values") or []
            if values and isinstance(values[0], dict):
                return str(values[0].get("identifier") or values[0].get("displayValue") or "")
    return None


def snapshot_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""), "serialNumber": item_serial(item),
        "subject": item.get("subject"), "status": item_status(item),
        "ownerId": item_user_id(item), "parentId": item.get("parentId"),
        "logicalStatus": item.get("logicalStatus"), "gmtModified": item.get("gmtModified"),
    }


def decimal_field_value(value: Any) -> str | None:
    """Serialize Yunxiao float custom fields with an explicit decimal point."""
    if value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise core.AdapterError("预计工时必须为数字。") from exc
    if not number.is_finite():
        raise core.AdapterError("预计工时必须为有限数字。")
    text = format(number, "f")
    return text if "." in text else text + ".0"


def validate_dates(start: str, finish: str, estimated_hours: str | None) -> None:
    try:
        start_date = dt.date.fromisoformat(start)
        finish_date = dt.date.fromisoformat(finish)
    except ValueError as exc:
        raise core.AdapterError("计划日期必须使用YYYY-MM-DD。") from exc
    if start_date > finish_date:
        raise core.AdapterError("计划开始不得晚于计划完成。")
    if estimated_hours is not None:
        if Decimal(decimal_field_value(estimated_hours) or "0") <= 0:
            raise core.AdapterError("预计工时必须为正数。")


def build_preflight(executable: str, args: argparse.Namespace) -> dict[str, Any]:
    validate_dates(args.plan_start, args.plan_finish, args.estimated_hours)
    estimated_hours = decimal_field_value(args.estimated_hours)
    project = resolve_project(executable, args.task, args.space_id)
    project_id = str(project["id"])
    delivery = find_workitem_by_serial(executable, project_id, "Task", args.task)
    if not str(delivery.get("subject") or "").startswith("【交付】"):
        raise core.AdapterError("来源任务标题不是【交付】任务。")
    if str((delivery.get("assignedTo") or {}).get("name") or "") != "何斐":
        raise core.AdapterError("来源【交付】负责人不是何斐。")
    delivery_status = item_status(delivery)
    if delivery_status == "已完成":
        raise core.AdapterError("来源【交付】已完成，禁止重开生命周期。")
    if delivery_status not in {"待处理", "已分配", "处理中"}:
        raise core.AdapterError(f"来源【交付】状态{delivery_status}不允许分配。")

    associated_ids = relation_ids(executable, str(delivery["id"]), "ASSOCIATED")
    associated = [get_workitem(executable, value) for value in associated_ids]
    requirements = [row for row in associated if row.get("categoryId") == "Req"
                    and core.is_normal_workitem(row)]
    if len(requirements) != 1 or item_status(requirements[0]) != "待开发":
        raise core.AdapterError("来源【交付】未唯一关联状态为待开发的产品需求。")
    requirement = requirements[0]

    child_ids = relation_ids(executable, str(delivery["id"]), "SUB")
    children = [get_workitem(executable, value) for value in child_ids]
    dev_children = [row for row in children if core.is_normal_workitem(row)
                    and str(row.get("subject") or "").startswith("【开发】")]
    if args.development_task:
        selected = [row for row in dev_children
                    if item_serial(row) == args.development_task]
        if len(selected) != 1:
            raise core.AdapterError("显式开发任务不是该交付下唯一有效【开发】子任务。")
        development = selected[0]
        action = "reuse"
    elif len(dev_children) == 0:
        development = None
        action = "create"
    elif len(dev_children) == 1:
        development = dev_children[0]
        action = "reuse"
    else:
        raise core.AdapterError("交付下存在多条【开发】任务，请显式提供--development-task。")
    if development and item_status(development) != "待处理":
        raise core.AdapterError("复用开发任务必须保持待处理，禁止状态回退。")

    owner = resolve_owner(executable, args.owner)
    if action == "create" and owner is None:
        raise core.AdapterError("CLI创建工作项要求负责人ID；负责人未唯一解析，停止创建。")

    type_id = str((delivery.get("workitemType") or {}).get("id") or "")
    if not type_id:
        raise core.AdapterError("来源任务缺少工作项类型ID。")
    fields = workitem_type_fields(executable, project_id, type_id)
    field_ids = {
        "planStart": unique_field_id(fields, "计划开始时间", "date"),
        "planFinish": unique_field_id(fields, "计划完成时间", "date"),
        "estimatedHours": unique_field_id(fields, "预计工时", "float"),
    }
    status_ids = {
        "todo": workflow_status_id(executable, project_id, type_id, "待处理"),
        "assigned": workflow_status_id(executable, project_id, type_id, "已分配"),
    }
    live_scope = {
        "projectId": project_id,
        "delivery": snapshot_item(delivery),
        "requirement": snapshot_item(requirement),
        "deliveryAssociatedIds": associated_ids,
        "deliverySubIds": child_ids,
        "developmentChildren": [snapshot_item(row) for row in dev_children],
        "selectedDevelopment": snapshot_item(development) if development else None,
        "owner": owner,
        "fieldIds": field_ids,
        "statusIds": status_ids,
    }
    return {
        "schema": SCHEMA, "command": "preflight", "createdAt": core.now_utc(),
        "input": {
            "task": args.task, "owner": args.owner, "planStart": args.plan_start,
            "planFinish": args.plan_finish, "estimatedHours": estimated_hours,
            "developmentTask": args.development_task, "spaceId": args.space_id,
        },
        "currentUser": core.current_user(executable),
        "action": action, "liveScope": live_scope,
        "scopeFingerprint": canonical_hash(live_scope),
    }


def write_preflight(value: dict[str, Any], output: str | None) -> Path:
    value["preflightHash"] = canonical_hash(value, {"preflightHash"})
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(output) if output else core.output_dir() / f"allocation-preflight-{stamp}.json"
    core.write_json(path, value)
    return path


def load_preflight(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise core.AdapterError("分配预检格式或版本不受支持。")
    if value.get("preflightHash") != canonical_hash(value, {"preflightHash"}):
        raise core.AdapterError("分配预检哈希不一致，拒绝写入。")
    return value


def args_from_preflight(value: dict[str, Any]) -> argparse.Namespace:
    source = value.get("input") or {}
    return argparse.Namespace(
        task=source.get("task"), owner=source.get("owner"),
        plan_start=source.get("planStart"), plan_finish=source.get("planFinish"),
        estimated_hours=source.get("estimatedHours"),
        development_task=source.get("developmentTask"), space_id=source.get("spaceId"),
    )


def ensure_relation(executable: str, source_id: str, relation_type: str,
                    target_id: str) -> str:
    if target_id in relation_ids(executable, source_id, relation_type):
        return "idempotent"
    core.run_devops(executable, [
        "projex-create-workitem-relation-record", "--id", source_id,
        "--relation-type", relation_type, "--workitem-id", target_id,
    ])
    if target_id not in relation_ids(executable, source_id, relation_type):
        raise core.AdapterError(f"关系{relation_type}创建后回读失败。")
    return "created"


def list_estimated_efforts(executable: str, workitem_id: str) -> list[dict[str, Any]]:
    value = core.unwrap(core.run_devops(executable, [
        "projex-list-estimated-efforts", "--id", workitem_id,
    ]))
    if value is None:
        return []
    if not isinstance(value, list):
        raise core.AdapterError("预计工时明细返回结构异常。")
    return [row for row in value if isinstance(row, dict)]


def estimated_effort_total(records: list[dict[str, Any]]) -> str:
    total = Decimal("0")
    try:
        for record in records:
            total += Decimal(str(record.get("spentTime") or "0"))
    except InvalidOperation as exc:
        raise core.AdapterError("预计工时明细包含非数字值。") from exc
    return decimal_field_value(total) or "0.0"


def ensure_estimated_effort(executable: str, workitem_id: str, owner_id: str,
                            expected_hours: str) -> dict[str, Any]:
    expected = decimal_field_value(expected_hours) or "0.0"
    records = list_estimated_efforts(executable, workitem_id)
    if Decimal(estimated_effort_total(records)) == Decimal(expected):
        return {"operation": "ensure-estimated-effort", "result": "idempotent",
                "estimatedHours": expected}
    if not records:
        core.run_devops(executable, [
            "projex-create-estimated-effort", "--id", workitem_id,
            "--description", "开发任务计划工时", "--owner", owner_id,
            "--spent-time", expected,
        ])
        result = "created"
    elif len(records) == 1 and records[0].get("id"):
        record = records[0]
        core.run_devops(executable, [
            "projex-update-estimated-effort", "--workitem-id", workitem_id,
            "--id", str(record["id"]), "--description",
            str(record.get("description") or "开发任务计划工时"),
            "--owner", owner_id, "--spent-time", expected,
        ])
        result = "updated"
    else:
        raise core.AdapterError("开发任务存在多条预计工时明细且合计不匹配，拒绝覆盖。")
    actual = estimated_effort_total(list_estimated_efforts(executable, workitem_id))
    if Decimal(actual) != Decimal(expected):
        raise core.AdapterError("预计工时登记后回读合计不一致。")
    return {"operation": "ensure-estimated-effort", "result": result,
            "estimatedHours": expected}


def create_development(executable: str, scope: dict[str, Any],
                       owner_id: str) -> dict[str, Any]:
    delivery = scope["delivery"]
    title = str(delivery.get("subject") or "")
    subject = title.replace("【交付】", "【开发】", 1)
    custom = {
        scope["fieldIds"]["planStart"]: scope["input"]["planStart"] + " 00:00:00",
        scope["fieldIds"]["planFinish"]: scope["input"]["planFinish"] + " 23:59:59",
    }
    # The create command coerces a whole decimal such as 16.0 to JSON integer 16,
    # which Projex rejects for float fields. Set hours through the generic update
    # command immediately after creation, where the decimal string is preserved.
    cli_args = [
        "projex-create-workitem", "--assigned-to", owner_id,
        "--space-id", scope["projectId"], "--subject", subject,
        "--workitem-type-id", scope["workitemTypeId"],
        "--parent-id", delivery["id"], "--format-type", "MARKDOWN",
        "--custom-field-values", json.dumps(custom, ensure_ascii=False, separators=(",", ":")),
    ]
    sprint_id = scope.get("sprintId")
    if sprint_id:
        cli_args.extend(["--sprint", sprint_id])
    value = core.unwrap(core.run_devops(executable, cli_args))
    workitem_id = str((value or {}).get("id") if isinstance(value, dict) else "")
    if not workitem_id:
        raise core.AdapterError("创建开发任务后未取得内部ID。")
    return get_workitem(executable, workitem_id)


def cmd_doctor(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    flags = core.require_auth_env()
    result = {
        "schema": SCHEMA, "command": "doctor", "ready": True,
        "cliVersion": core.run_raw(executable, ["version"]),
        "pluginVersion": core.run_raw(executable, ["devops", "version"]),
        "credentialFlags": flags, "currentUser": core.current_user(executable),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    value = build_preflight(executable, args)
    path = write_preflight(value, args.output)
    print(json.dumps({
        "schema": SCHEMA, "command": "preflight", "ready": True,
        "preflightPath": str(path), "preflightHash": value["preflightHash"],
        "action": value["action"], "project": value["liveScope"]["projectId"],
        "delivery": value["liveScope"]["delivery"],
        "requirement": value["liveScope"]["requirement"],
        "development": value["liveScope"]["selectedDevelopment"],
        "owner": value["liveScope"]["owner"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    executable = core.find_aliyun()
    core.require_auth_env()
    frozen = load_preflight(args.preflight)
    current = build_preflight(executable, args_from_preflight(frozen))
    if current.get("scopeFingerprint") != frozen.get("scopeFingerprint"):
        raise core.AdapterError("预检后工作项、关系、负责人或字段配置已变化，请重新预检。")

    source = frozen["input"]
    live = frozen["liveScope"]
    scope = {
        **live, "input": source,
        "workitemTypeId": str((get_workitem(executable, live["delivery"]["id"])
                                .get("workitemType") or {}).get("id") or ""),
        "sprintId": str((get_workitem(executable, live["delivery"]["id"])
                         .get("sprint") or {}).get("id") or "") or None,
    }
    operations: list[dict[str, Any]] = []
    owner = live.get("owner")
    if frozen["action"] == "create":
        development = create_development(executable, scope, str(owner["id"]))
        operations.append({"operation": "create-development", "result": "created",
                           "serialNumber": item_serial(development)})
    else:
        development = get_workitem(executable, live["selectedDevelopment"]["id"])
        operations.append({"operation": "reuse-development", "result": "idempotent",
                           "serialNumber": item_serial(development)})

    description, format_type = managed_description(
        development.get("description"), development.get("formatType"), item_serial(development))
    update_body: dict[str, Any] = {
        live["fieldIds"]["planStart"]: source["planStart"] + " 00:00:00",
        live["fieldIds"]["planFinish"]: source["planFinish"] + " 23:59:59",
        "description": description, "formatType": format_type,
    }
    if owner:
        update_body["assignedTo"] = owner["id"]
    if item_status(development) != "待处理":
        raise core.AdapterError("开发任务不再是待处理，拒绝状态回退。")
    current_values = {
        "owner": item_user_id(development),
        "planStart": field_value(development, live["fieldIds"]["planStart"]),
        "planFinish": field_value(development, live["fieldIds"]["planFinish"]),
        "estimatedHours": field_value(development, live["fieldIds"]["estimatedHours"]),
        "description": str(development.get("description") or ""),
        "formatType": str(development.get("formatType") or "MARKDOWN").upper(),
    }
    desired_owner = str(owner["id"]) if owner else current_values["owner"]
    needs_update = any((
        current_values["owner"] != desired_owner,
        current_values["planStart"] != source["planStart"] + " 00:00:00",
        current_values["planFinish"] != source["planFinish"] + " 23:59:59",
        current_values["description"] != description,
        current_values["formatType"] != format_type,
    ))
    if needs_update:
        core.run_devops(executable, [
            "projex-update-workitem", "--id", str(development["id"]),
            "--biz-body", json.dumps(update_body, ensure_ascii=False, separators=(",", ":")),
        ])
        operations.append({"operation": "update-development-fields", "result": "updated"})
    else:
        operations.append({"operation": "update-development-fields", "result": "idempotent"})

    if source.get("estimatedHours") is not None:
        operations.append(ensure_estimated_effort(
            executable, str(development["id"]), desired_owner,
            str(source["estimatedHours"]),
        ))

    parent_result = ensure_relation(executable, str(development["id"]), "PARENT",
                                    live["delivery"]["id"])
    associated_result = ensure_relation(executable, str(development["id"]), "ASSOCIATED",
                                        live["requirement"]["id"])
    operations.extend([
        {"operation": "ensure-parent", "result": parent_result},
        {"operation": "ensure-requirement", "result": associated_result},
    ])

    after_development = get_workitem(executable, str(development["id"]))
    expected = {
        "owner": str(owner["id"]) if owner else item_user_id(development),
        "planStart": source["planStart"] + " 00:00:00",
        "planFinish": source["planFinish"] + " 23:59:59",
        "estimatedHours": decimal_field_value(source.get("estimatedHours")),
    }
    actual = {
        "owner": item_user_id(after_development),
        "planStart": field_value(after_development, live["fieldIds"]["planStart"]),
        "planFinish": field_value(after_development, live["fieldIds"]["planFinish"]),
        "estimatedHours": estimated_effort_total(
            list_estimated_efforts(executable, str(development["id"]))),
    }
    if actual["owner"] != expected["owner"] or actual["planStart"] != expected["planStart"] \
            or actual["planFinish"] != expected["planFinish"]:
        raise core.AdapterError("开发任务负责人或计划日期写入后回读不一致。")
    if expected["estimatedHours"] is not None and Decimal(
            actual["estimatedHours"]) != Decimal(expected["estimatedHours"]):
        raise core.AdapterError("开发任务预计工时写入后回读不一致。")
    if item_status(after_development) != "待处理":
        raise core.AdapterError("开发任务状态回读不是待处理。")
    if live["delivery"]["id"] not in relation_ids(executable, str(development["id"]), "PARENT"):
        raise core.AdapterError("开发任务父交付关系回读失败。")
    if live["requirement"]["id"] not in relation_ids(executable, str(development["id"]), "ASSOCIATED"):
        raise core.AdapterError("开发任务需求关联回读失败。")
    expected_command = f"/go 开发任务:任务={item_serial(after_development)}"
    if expected_command not in str(after_development.get("description") or ""):
        raise core.AdapterError("开发任务下一阶段命令回读失败。")

    before_delivery_status = item_status(get_workitem(executable, live["delivery"]["id"]))
    if before_delivery_status == "待处理":
        body = json.dumps({"status": live["statusIds"]["assigned"]},
                          ensure_ascii=False, separators=(",", ":"))
        core.run_devops(executable, [
            "projex-update-workitem", "--id", live["delivery"]["id"], "--biz-body", body,
        ])
        operations.append({"operation": "update-delivery-status", "result": "updated",
                           "before": "待处理", "after": "已分配"})
    elif before_delivery_status in {"已分配", "处理中"}:
        operations.append({"operation": "update-delivery-status", "result": "idempotent",
                           "before": before_delivery_status, "after": before_delivery_status})
    else:
        raise core.AdapterError(f"交付状态已变化为{before_delivery_status}，拒绝写入。")
    after_delivery = get_workitem(executable, live["delivery"]["id"])
    if item_status(after_delivery) not in {"已分配", "处理中"}:
        raise core.AdapterError("交付任务状态写入后回读失败。")
    if item_user_id(after_delivery) != live["delivery"]["ownerId"]:
        raise core.AdapterError("交付任务负责人发生变化。")
    after_requirement = get_workitem(executable, live["requirement"]["id"])
    if item_status(after_requirement) != "待开发":
        raise core.AdapterError("需求状态不再是待开发。")

    receipt = {
        "schema": SCHEMA, "command": "apply", "createdAt": core.now_utc(),
        "preflightPath": str(Path(args.preflight)),
        "preflightHash": frozen["preflightHash"], "operations": operations,
        "delivery": snapshot_item(after_delivery),
        "requirement": snapshot_item(after_requirement),
        "development": snapshot_item(after_development), "fields": actual,
    }
    receipt["receiptHash"] = canonical_hash(receipt, {"receiptHash"})
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(args.receipt) if args.receipt else core.output_dir() / f"allocation-apply-{stamp}.json"
    core.write_json(path, receipt)
    print(json.dumps({**receipt, "receiptPath": str(path)}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Official aliyun devops CLI adapter for 分配任务")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="检查CLI、插件和中心版环境变量")
    doctor.set_defaults(func=cmd_doctor)
    preflight = sub.add_parser("preflight", help="只读解析交付、需求、开发任务、负责人和字段")
    preflight.add_argument("--task", required=True)
    preflight.add_argument("--owner", required=True)
    preflight.add_argument("--plan-start", required=True)
    preflight.add_argument("--plan-finish", required=True)
    preflight.add_argument("--estimated-hours")
    preflight.add_argument("--development-task")
    preflight.add_argument("--space-id")
    preflight.add_argument("--output")
    preflight.set_defaults(func=cmd_preflight)
    apply = sub.add_parser("apply", help="仅按未漂移预检回执执行并回读")
    apply.add_argument("--preflight", required=True)
    apply.add_argument("--receipt")
    apply.set_defaults(func=cmd_apply)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (core.AdapterError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": SCHEMA, "result": "blocked",
                          "error": core.scrub(str(exc))}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
