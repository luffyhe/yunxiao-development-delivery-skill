#!/usr/bin/env python3
"""Shared, secret-safe runtime for official aliyun devops CLI adapters."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TOKEN_RE = re.compile(r"pt-[A-Za-z0-9_\-]+")
QUERY_SECRET_RE = re.compile(r"(?i)(access_token|token|signature)=([^&\s\"']+)")
NAMED_SECRET_RE = re.compile(
    r"(?im)^(\s*(?:secret|secretKey|password|credential)\s*[:=]\s*)(.+)$"
)
SEC_VALUE_RE = re.compile(r"\bSEC[A-Za-z0-9_\-]{16,}\b")


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
    cleaned = QUERY_SECRET_RE.sub(
        lambda match: f"{match.group(1)}=<redacted-secret>", cleaned
    )
    cleaned = NAMED_SECRET_RE.sub(
        lambda match: f"{match.group(1)}<redacted-secret>", cleaned
    )
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
    raise AdapterError("未找到aliyun CLI。请安装官方阿里云CLI和aliyun-cli-devops插件。")


def require_auth_env() -> dict[str, bool]:
    flags = {
        "token": bool(os.environ.get("ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN")),
        "organizationId": bool(
            os.environ.get("ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID")
        ),
        "apiBaseUrl": bool(os.environ.get("ALIBABA_CLOUD_YUNXIAO_API_BASE_URL")),
    }
    if not flags["token"]:
        raise AdapterError(
            "缺少ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN。请在本机安全设置PAT。"
        )
    if not flags["organizationId"] and not flags["apiBaseUrl"]:
        raise AdapterError(
            "中心版需设置ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID；Region版需设置ALIBABA_CLOUD_YUNXIAO_API_BASE_URL。"
        )
    return flags


def run_raw(executable: str, args: list[str], timeout: int = 120,
            scrub_output: bool = True) -> str:
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
    completed = subprocess.run([executable, *args], **kwargs)
    raw_stdout = completed.stdout.strip()
    stdout = scrub(raw_stdout)
    stderr = scrub(completed.stderr).strip()
    if completed.returncode != 0:
        detail = stderr or stdout or f"exit={completed.returncode}"
        raise AdapterError(f"CLI调用失败：{' '.join(args[:2])}；{detail}")
    return stdout if scrub_output else raw_stdout


def run_devops(executable: str, args: list[str], timeout: int = 120) -> Any:
    text = run_raw(executable, ["devops", *args], timeout=timeout, scrub_output=False)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AdapterError(
            f"CLI返回的不是JSON：{args[0] if args else ''}；{scrub(text[:500])}"
        ) from exc


def unwrap(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("result", "data"):
            if key in value and len(value) <= 4:
                return value[key]
    return value


def current_user(executable: str) -> dict[str, Any]:
    value = unwrap(run_devops(executable, ["base-get-user-by-token"]))
    if not isinstance(value, dict) or not value.get("id"):
        raise AdapterError("PAT用户回读失败，未取得唯一用户ID。")
    return {
        "id": value.get("id"),
        "name": value.get("name") or value.get("nickName"),
    }
