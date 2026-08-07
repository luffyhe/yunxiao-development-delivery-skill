# AGENTS.md

## Cursor Cloud specific instructions

This repository packages the `yunxiao-development-delivery` Skill. It is **not**
a long-running server/web app — it is a set of Python CLI adapters (under
`skills/yunxiao-development-delivery/scripts/`) that wrap the official
`aliyun devops` CLI, a unit-test suite, and a PowerShell packaging tool.

### Services / components

- **Python CLI adapters** — the runnable "application". Entry points are the
  `*.py` files in `skills/yunxiao-development-delivery/scripts/`, invoked through
  the launcher `run-skill-script.sh` (macOS/Linux) or `run-skill-script.ps1`
  (Windows). The launcher only runs `.py` files inside that same `scripts/`
  directory (no absolute/relative paths or path traversal).
- **Unit tests** — `tests/test_yunxiao_cli_adapters.py`.
- **Packaging tool** — `tools/build-dual-client-packages.ps1` (requires PowerShell).

### Dependencies

- Python 3 only, **standard library exclusively** — there is no
  `requirements.txt`/`package.json` and nothing to `pip install`.
- The packaging tool needs `pwsh` (PowerShell 7). It is preinstalled in the VM
  snapshot; it is a system tool, not a code dependency, so it is not in the
  update script.

### Lint / test / build / run

- Tests: `python3 -m unittest discover -s tests -v`
- Static check (no linter is configured): `python3 -m py_compile skills/yunxiao-development-delivery/scripts/*.py tests/*.py`
- Build packages: `pwsh -File ./tools/build-dual-client-packages.ps1`
- Run an adapter: `sh skills/yunxiao-development-delivery/scripts/run-skill-script.sh yunxiao_cli_gateway.py doctor`

### Non-obvious caveats

- **Running the adapters normally requires the real `aliyun devops` CLI plus
  Yunxiao credentials** (env vars `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN` and either
  `ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID` or `ALIBABA_CLOUD_YUNXIAO_API_BASE_URL`).
  Without the CLI, `doctor` intentionally returns a structured
  `{"result":"blocked", ...}` JSON and exits `69` — this is correct behavior, not
  a setup failure. The adapters never fall back to browser/DOM/Cookie access.
- To exercise the guarded-transaction pipeline (doctor → read → preflight →
  apply) end-to-end **without live Yunxiao access**, point `ALIYUN_CLI_PATH` at a
  local stub executable that answers `aliyun devops <operation>` with JSON on
  stdout, and set the auth env vars to any placeholder values. The real adapter
  code (plan validation, hashed preflight, drift check, single write, read-back,
  idempotent receipt) then runs unchanged.
- The build tool **regenerates `packages/**`**. The generated `.zip` SHA-256
  differs on every run (zip embeds file timestamps), and Linux `pwsh 7` formats
  `manifest.json` differently than the committed Windows-built artifacts (BOM +
  indentation). Treat `packages/**` as build output: verify the build succeeds
  but do **not** commit the regenerated files unless intentionally re-releasing.
- The Cursor package intentionally strips the Codex-only `agents/` directory;
  the Codex package keeps it. A correct build yields 22 entries (cursor) vs 23
  (codex).
