---
name: yunxiao-development-delivery
description: "Manage Yunxiao development after a YunxiaoPM handoff entirely through the official aliyun devops CLI for Yunxiao Projex, Codeup, Flow, and AppStack reads/writes: accept 【交付】, allocate and complete 【开发】 tasks, repair Bugs, submit branches/MRs, prepare test handoff, handle release repair, and clean branches. Every platform mutation uses a read-only snapshot, hashed preflight, drift check, one write pass, targeted read-back, and idempotent receipt; browser, DOM, Cookie, visual clicking, and webpage-internal APIs are forbidden fallbacks. Local code editing, tests, commit, and push remain native local actions. Development owns 【交付】 only 待处理→已分配→处理中; YunxiaoPM closes it after acceptance."
---

# Yunxiao Development Delivery

Operate development tasks and Codeup assets without using code activity as a substitute for real work state. Suite version: `9.0.0`.

## Load the required references

Read each selected file completely before acting:

- Development task, Codeup, stage-task and OneOS controls: [references/controls.md](references/controls.md).
- Short Chinese commands and defect-fix workflow: [references/commands.md](references/commands.md).
- `开发任务:任务=<ID>` direct/plan modes, 新增/优化材料门禁, prototype comparison, and implementation completion: [references/implementation-materials.md](references/implementation-materials.md).
- Codex task association, active-duration accounting, minute-to-hour conversion, and completion-field writeback: [references/codex-time-accounting.md](references/codex-time-accounting.md).
- Batch `/go` discovery, stable snapshots, per-task continuation, worktree isolation, and final reporting: [references/batch-execution.md](references/batch-execution.md).
- Mandatory per-node operation ledger, Git-grounded file inventory, batch attribution, and blocker reporting: [references/change-reporting.md](references/change-reporting.md).
- YunxiaoPM handoff input, idempotency, and downstream rotation: [references/yunxiaopm-handoff.md](references/yunxiaopm-handoff.md).
- Mandatory iteration resolution, normal-requirement test deployment, and release-repair re-entry: [references/test-deployment-handoff.md](references/test-deployment-handoff.md).
- Authorization, live-change safety, evidence, and cross-skill handoff: [references/safety-handoff.md](references/safety-handoff.md).
- Independent release-task branch cleanup, retention, remote deletion, and current-machine local cleanup: [references/release-branch-cleanup.md](references/release-branch-cleanup.md).
- For every Yunxiao platform read/write not already covered by a specialized adapter, read the official CLI gateway, transaction-plan, idempotency, and performance rules: [references/yunxiao-cli-runtime.md](references/yunxiao-cli-runtime.md).
- For `分配任务`, read the official CLI environment, hashed preflight/apply receipt, idempotency, field, relation, and read-back rules: [references/yunxiao-cli-allocation.md](references/yunxiao-cli-allocation.md).
- For `/go 修复负责人是我的所有Bug`, read the official CLI adapter, credentials, frozen snapshot, status-write, and fallback rules: [references/yunxiao-cli-bug-batch.md](references/yunxiao-cli-bug-batch.md).
- Run bundled Python through the cross-platform launcher contract in [references/runtime-launcher.md](references/runtime-launcher.md).

The safeguards in this Skill are self-contained. If `git-submit-safety` is also installed, use it as an additional repository-specific guardrail.

## Own only the development boundary

Own these outcomes:

1. Accept a verified YunxiaoPM handoff whose requirement is already `待开发`.
2. Allocate one or more `【开发】` child tasks with developer, planned dates, and estimated hours, then move the source `【交付】` task from `待处理` to `已分配`.
3. Record the developer's real start and move the development child, source `【交付】` task, and requirement into development.
4. Create branches, commits, and merge requests, and attempt requirement/development-task association without making association success a gate.
5. In `完成开发`, run an independent developer-side completion validation, submit and merge all relevant MRs without waiting for review, CI, or discussion state, then write the development task's actual completion time and Codex-derived actual development hours before marking it complete.
6. Use one `修复bug:<BUG-ID>` node to inspect, reproduce, select the requirement development branch or a new Bug branch, fix, verify, submit, deploy to test, and set the exact defect to `已修复` for tester verification. Preserve `验证人/验证者` exactly as created by `YunxiaoQA`.
7. Resolve exactly one iteration from the source delivery, resolve exactly one project user with role `测试主管`, create or reuse the unique `【测试】` task as a formal child of the source `【交付】` task and associate it with the requirement, force its owner to that user's ID, deploy the merged normal-requirement version to test, write and verify `oneos.test-deployment/v1`, then move the requirement from `开发完成` to `待测试` and produce the formal test handoff.
8. Hand formal case execution, retest, Bug closure, test evidence, and requirement test-stage transitions to `YunxiaoQA` only after the test task and requirement handoff are ready.
9. Run `/go 实现所有负责人是我的开发任务` as a stable batch that attempts every active assigned development task without letting one task-level blocker abort the remaining queue.
10. Run `/go 修复负责人是我的所有Bug` as a stable consolidated batch: use `yunxiao_cli_bug_batch.py` through official `aliyun devops` CLI to freeze and update the current developer-actionable Bug list; use `yunxiao_cli_bug_delivery.py` to preflight/create Codeup branches, create/read/merge MRs, and start or attach to exactly one Flow test run. Edit, test, commit, and push locally only after the immutable plan passes; never perform Yunxiao platform writes through browser/DOM/Cookie fallback. Use the same frozen snapshot plus CLI-generated deployment evidence to move successfully deployed Bugs to `已修复` with exact read-back while preserving every Bug's existing `验证人/验证者`.
11. For every write-capable development, completion, and Bug node, emit the exact operations performed and the complete task-owned code-file inventory required by `references/change-reporting.md`; batch output must retain per-task or per-Bug attribution.
12. On `处理发布回流：发版任务=<ID>`, consume only a verified release/acceptance incident and QA-created Bug set, repair the frozen Bugs with the existing consolidated submission rules, perform one test deployment, and hand the exact release repair batch back to `YunxiaoQA` for per-Bug retest.
13. On `清理分支：发版任务=<ID>`, require the release task to be `已完成` after product acceptance and verify the shared `oneos.product-acceptance/v1` evidence before cleaning eligible exact Codeup branches; `发布完成` alone must block cleanup. Safely clean matching branches on the current machine when possible, and report branches that other developers must clean on their own machines.

This Skill does not impersonate the tester: developer-side automated tests and real-page checks prove implementation readiness only. Formal case execution, current-run result recording, retest, Bug closure, and `待测试→测试中→测试完成` belong to `YunxiaoQA` after handoff. Do not publish production; hand release actions to `$yunxiao-release-operations`.

## Cross-Skill logical handoff

- Accept and emit only formal Skill names, exact requirement/delivery/development/test/release IDs, live states, formal `ASSOCIATED`/`TASK_SUB` relations, and necessary MR, commit, pipeline, deployment, evidence, or idempotency identifiers.
- Never discover, read, copy, or require another Skill's installation directory. This Skill owns its bundled resources; missing Yunxiao context must be resolved from the explicit handoff IDs and live services.
- Downstream selectors are `/skill YunxiaoQA` and `/skill yunxiao-release-operations`; product return is `/skill YunxiaoPM`. Never emit a legacy alias or a filesystem path as a command.

Command state contract:

| Command | Allowed lifecycle effect |
|---|---|
| `接收产品交棒` | Read and validate only; no task or state writes |
| `分配任务` | Create/reuse `【开发】`; `【交付】待处理→已分配`; requirement stays `待开发` |
| `开发任务` / batch development | Development child `待处理→处理中`; first child also moves `【交付】已分配→处理中` and requirement `待开发→开发中` |
| `完成开发` | Complete the named development child; only after all development children complete, move requirement `开发中→开发完成`, prepare `【测试】`, require one iteration and a proven test deployment, then move to `待测试`; keep `【交付】=处理中` |
| Bug repair / batch Bug repair | Change only the named Bug `状态` and code assets; preserve `验证人/验证者`; never move the requirement or `【交付】` |
| `处理发布回流` | Repair only QA-created Bugs formally tied to the release incident; one consolidated test deployment; no production or product-state writes |
| Branch cleanup | Change only eligible branches; never move a work item |

`【交付】` is the lifecycle container. This Skill must never perform `【交付】处理中→已完成`; that transition belongs to `YunxiaoPM` after production acceptance.

## Classify authority

- `audit`: inspect code assets, states, and logs only.
- `plan`: prepare tasks, branch/MR plan, or fix plan only.
- `apply`: create or modify exact named development tasks and formal relations.
- `fix`: edit code after root cause and scope are verified.
- `submit`: commit, push, open, or merge an MR only inside an explicitly invoked `/go 完成开发` for the exact development task, `修复bug:<BUG-ID>` for the exact Bug, or the final consolidated-submission phase of `/go 修复负责人是我的所有Bug`.
- `cleanup`: delete only exact eligible remote branches and safe matching local branches under an explicitly invoked `清理分支：发版任务=<ID>`.
- `document`: produce a development handoff or diagnosis report.

Creating a Bug does not authorize a fix. Generic diagnosis or code editing does not authorize submission. Only an explicit `/go 完成开发` grants exact-task submission and a direct platform-permitted merge attempt, while `修复bug:<BUG-ID>` grants the same restricted submission authority only for that Bug's verified repositories and test integration path. The Bug batch grants submission only after the frozen queue's edit loop ends, limited to one consolidated commit/MR sequence per repository-and-branch group and one compatible test deployment for the batch. Only `清理分支：发版任务=<ID>` grants branch-deletion authority, limited to the exact release scope and the gates in `references/release-branch-cleanup.md`.

`开发任务:任务=<ID> 输出执行方案` initially grants only `audit + plan`. Do not write Yunxiao, create branches, edit code, run state-changing test actions, or mark the goal complete while waiting. An explicit confirmation in the same Codex task upgrades the exact unchanged plan snapshot to `apply + fix`. `开发任务:任务=<ID>` without the suffix grants `apply + fix` directly after the same internal analysis and gates, without displaying or waiting on the plan. The development-task batch grants the same direct-execution authority separately for each task in its initial snapshot. `/go 完成开发` additionally grants `submit + direct merge attempt` for that task's verified repositories and actual integration branches. `修复bug:<BUG-ID>` grants `apply + fix + submit + direct merge attempt + test-deployment coordination` only for the named Bug and its evidence-resolved target codebase. The Bug batch grants `apply + fix` per frozen Bug during its edit loop, then grants one consolidated `submit + direct merge attempt` phase per repository-and-branch group and exactly one batch test-deployment coordination action; it never invokes end-to-end single-Bug submission inside the loop. Review approval, CI result, and discussion resolution are not inspected, awaited, or used as Skill gates. Self-approval is allowed when Codeup exposes it and the current account is permitted to use it, but it is not required. These commands never grant production deployment, force push, administrator bypass, protection-rule disabling, unrelated refactoring, tester impersonation, or Bug closure.

## Execute

All Yunxiao Projex, Codeup, Flow, and AppStack discovery, state reads, relation reads, writes, pipeline actions, logs, and read-back must use the bundled official CLI adapters. Prefer the specialized allocation and Bug adapters; otherwise use `yunxiao_cli_gateway.py`. Never use a browser, screenshot/OCR, semantic DOM, Cookie, connector, or webpage-internal API for Yunxiao platform work, including as a fallback after CLI failure. Browser-based real-page verification is permitted only for the application being developed and never as Yunxiao evidence.

1. For development-task commands, resolve the exact project, requirement, numbered `【交付】` task, development task, repository, and real integration branch. For Bug commands, resolve the exact Bug and project first; Bug relations and repository fields are optional inputs.
2. Re-read the live requirement and `【交付】` task using the explicit YunxiaoPM identifiers. Accept only the contract in `references/yunxiaopm-handoff.md`; never search or deduplicate by title. For `分配任务`, perform these reads only through `yunxiao_cli_allocate_task.py` and official `aliyun devops` CLI.
3. For `分配任务`, first run `skill-run yunxiao_cli_allocate_task.py doctor`, then translate the user parameters to `preflight --task ... --owner ... --plan-start ... --plan-finish ... [--estimated-hours ...] [--development-task ...]`. Interpret `任务=<ID>` as the source `【交付】` task. Validate planned start ≤ planned finish and positive optional hours. Reuse may preserve the existing owner when the name is not unique; creation must block when the owner cannot resolve because the official CLI requires `assignedTo`.
4. Only after the hashed read-only preflight passes, run `skill-run yunxiao_cli_allocate_task.py apply --preflight <回执>`. The adapter must re-preflight and reject drift, create/reuse `【开发】<需求标题>`, set developer/dates/hours while keeping `待处理`, create/read `PARENT→【交付】` and `ASSOCIATED→需求`, and aggregate-read every field and the managed next-stage command. Only then may it move the source `【交付】` from `待处理 → 已分配`; `已分配|处理中` remains idempotent and `已完成` blocks. Never use browser/DOM/Cookie fallback.
5. Upsert a managed `## 下一阶段` block in the development task description without overwriting business content. Its executable content is exactly `/skill yunxiao-development-delivery` followed by `/go 开发任务:任务=<开发任务编号>`; never append type, repository, scope, or baseline parameters. Mention the optional suffix `输出执行方案` as explanatory text outside the executable block only when useful. Trust only the CLI apply receipt and final CLI read-back.
6. Do not require repository information at allocation or from the active conversation. During `开发任务`, analyze the requirement, affected page/interface/data, project configuration, existing code relations, accessible Codeup repositories, and current workspace to determine the applicable frontend/backend project automatically. Missing conversation-supplied repository addresses never block the node; stop only when the evidence itself remains contradictory after discovery and the modification target cannot be made safe.
7. For initial development intake, require the requirement to be `待开发` and the source delivery task to be `已分配`. For a later sibling task, accept requirement=`开发中` and delivery=`处理中` only when the same delivery tree contains verified development-start evidence; for resuming this task, also require its immutable first-start record and formally associated branch. Never change `已确认`/`设计完成` to `待开发` here.
8. For `开发任务`, accept the explicit work-item ID without requiring it to be a `【开发】` child. Prefer a direct requirement relation, then derive the source requirement and scope from the task parent, title, description, attachments, project/iteration context, existing code assets, and repository facts. Missing `TASK_SUB` or `ASSOCIATED` relations alone never block execution. Derive `新增` or `优化` from the resolved requirement/task title and infer `前端`、`后端` or `全栈`.
9. Select exactly one mode:
   - `开发任务:任务=<ID> 输出执行方案`: completely read and validate the requirement, materials, relevant code and runtime facts; return a concrete executable plan and stop before every write. Keep the goal unfinished and wait for an explicit semantic confirmation such as `确认按方案执行 ONEOS-789`. On confirmation, re-read the requirement/material/code snapshot; if any execution-relevant fact changed, invalidate the plan and return a revised plan for confirmation instead of executing the stale plan.
   - `开发任务:任务=<ID>`: do not display a proposal or wait for confirmation. Build the same internal plan, run all gates, list the continuous execution tasks, and execute directly.
   A confirmation never overrides an unresolved mandatory gate or expands the confirmed scope.
10. Run the complete pre-write material gate in `references/implementation-materials.md`. For 优化, require a complete and implementable requirement description. For 新增, require downloaded attachments containing the detailed requirement and HTML prototype plus an accessible prototype URL in the requirement description; compare both prototypes and stop on material differences.
11. Only after material gates pass, use the developer's explicit start action as the authoritative start time. Persist the first real start timestamp once in a dedicated field when available; otherwise write a structured task comment. Never replace it with branch or commit time and never overwrite it on retry.
12. After the target project is automatically determined, inspect its real repository configuration and integration/default branches. Prefer frontend=`develop` and backend=`dev` when they exist, but absence of either name is not a gate; use the repository's verified actual integration branch and record the choice. Never create a branch name merely to satisfy this Skill.
13. Prefer `feature/<WORK-ITEM-ID>` or `fix/<BUG-ID>`. For every applicable repository, attempt to associate code assets with the requirement and development task. If either association is unsupported, unavailable, ambiguous, or fails read-back, record the result and continue; association success is not a branch, MR, merge, or completion gate. Defect fixes must still associate the Bug itself when Codeup supports that relation.
14. After the branch is created or reused, try native automation for `开发任务：待处理→处理中` and, for the first started child in the delivery tree, `【交付】任务：已分配→处理中` plus `产品需求：待开发→开发中`. Missing, disabled, or failed automation is not a gate: continue implementation and perform the same authorized state update directly or through the configured bridge, recording the actual method and result instead of claiming native automation passed. A later sibling starts only its own development task and does not repeat the parent or requirement transition.
15. Load `$apply-oneos-v2-frontend-guidelines` for frontend scope and `$alibaba-java-backend-guidelines` for Java backend scope. Inspect repository facts before editing, implement the validated material, and run proportionate automated and real-page verification. Do not treat source inspection as functional or visual verification.
16. For every requirement, finish developer-side verification after implementation: compile/static checks, unit/integration tests, and proportionate real-page checks against the implemented version. Fix developer-discovered failures within the same scope. Do not create a formal test run, write a tester result, close Bugs, or advance test-stage requirement states.
17. `开发任务` completes at verified implementation, developer-side validation, and task evidence. Formal QA completion is deliberately not a development-task gate because the `【测试】` task is created only in `完成开发`.
18. When `开发任务` passes, write a managed next-stage block containing `/skill yunxiao-development-delivery` and `/go 完成开发:任务=<开发任务编号>`. Do not commit, push, create an MR, merge, or deploy during `开发任务`.
19. For a batch `/go`, execute `references/batch-execution.md`: resolve the current account, freeze and display the active task snapshot, call this same single-task handler sequentially in isolated worktrees, record per-task active-duration segments and stops, and continue. A task-level stop never authorizes bypassing its gate.
20. For `/go 完成开发`, inspect the matching `开发任务` execution evidence when present, but do not use missing or incomplete execution evidence as a gate. Execute any still-missing material analysis, implementation, first validation, or start-state work inside the same completion goal before submission. Run a fresh developer-side completion validation against the final code and resolve every developer-discovered blocker before submission; do not fabricate formal QA evidence.
21. After completion validation passes, fetch/pull first, stop on code conflicts, rerun the Skill's own scoped verification, then commit, push, and create or reuse MRs for every applicable repository. Attempt to associate each MR with the requirement and development task; record `associated` or `skipped/failed` per relation and continue either way.
22. Do not inspect or wait for Codeup review approval, CI status, or discussion resolution. After MR creation, immediately attempt merge to the repository's verified actual integration branch. Self-approval is allowed but optional. Merge only when the target branch is correct, the MR has no code conflict, Codeup reports it technically mergeable, and the platform accepts the operation under current permissions and protection settings. If Codeup rejects the merge, report the exact platform response; never force push, use administrator bypass, or disable protection rules.
23. After every applicable MR for the exact development task is merged, execute `references/codex-time-accounting.md`. Set `实际完成时间` to the latest verified applicable-MR merge timestamp, converted to the Yunxiao project's timezone. Discover every uniquely associated Codex task or per-item batch segment, sum platform-reported active elapsed seconds, round the aggregate once to whole minutes, convert minutes to decimal hours, and write `实际开发工时`.
24. Read back `实际完成时间` and `实际开发工时`, persist the Codex task IDs/segments, total minutes, conversion expression, written hours, source timestamps, and rounding evidence, then move the exact development task to `已完成`. Do not mark it complete when any source is missing, duplicated, mixed across work items without segmentation, based only on wall-clock span, or rejected by field precision. The source delivery task remains `处理中` both while development children are unfinished and after they finish.
25. Verify every non-cancelled development task under the delivery tree is `已完成` and has its own read-back actual completion/time-accounting evidence. Then keep the source `【交付】` task at `处理中`, move only the requirement `开发中 → 开发完成`, and read both back. The delivery task is a cross-stage container and is closed only by `YunxiaoPM` after production acceptance. Historical development tasks missing either field require an evidence-backed backfill; never copy the current task's time or hours to a sibling.
26. Before creating or reusing a `【测试】` task, resolve the exact source `【交付】` task from the development task and requirement handoff, then read the current project's role membership and require exactly one user with role `测试主管`. Search for an existing valid test task by the same project, requirement, and delivery tree; never deduplicate by title alone. A role read failure, zero or multiple supervisors, multiple ambiguous test tasks, or an unresolved delivery task blocks only the test-handoff stage: do not create a new test task and do not move the requirement to `待测试`.
27. Create the new `【测试】` task directly under the source `【交付】` task, or make the single reusable task a child of that same delivery task. Require and read back both formal relations: `【测试】 TASK_SUB→【交付】` and `【测试】 ASSOCIATED→产品需求`. A reusable top-level task may be attached when unambiguous; a task already parented under a different delivery must not be detached or silently moved and blocks handoff. Explicitly set the owner to the resolved supervisor instead of accepting the creator, parent owner, delivery owner, developer, or platform default; replace any non-supervisor owner on a reusable task.
28. In the new or reused test task description, idempotently upsert a managed `## 开发交接` block with exactly two subsections: `### 测试建议` and `### 临时需求变更点`. Derive concrete test suggestions from the requirement, implementation, changed interfaces/data/permissions, verification evidence, scoped Bugs, MRs, environment prerequisites, boundary paths, and regression surface; never use a content-free phrase such as “全面测试”. Record only explicitly confirmed deviations from the original requirement as temporary changes, including the changed behavior, original behavior, reason, confirmation evidence, impact, and follow-up when known. If none exists, write `- 无（本次开发未发生已确认的临时需求变更）`. Preserve all human-authored description outside the managed block, and replace rather than duplicate the block on retry. An unconfirmed candidate that affects acceptance blocks test handoff instead of being recorded as a confirmed change.
29. Read back the test task's `TASK_SUB` parent ID, `ASSOCIATED` requirement ID, owner user ID, both managed headings, and their actual content. Parent ID must equal the source delivery task ID and requirement ID must equal the source product requirement ID. Any relation, owner, or description write/read-back mismatch blocks test handoff.
30. Resolve exactly one non-closed iteration formally containing the source `【交付】`. Zero, multiple, cross-project, title-only, or conflicting iteration matches block test handoff and return `/skill YunxiaoPM` plus the exact `创建迭代` remediation; do not silently invent an iteration.
31. After all applicable MRs are merged, trigger or verify exactly one test-environment deployment covering the full normal-requirement scope. Require environment=`test`, terminal success, execution ID/URL, deployed version or artifact, included commit/MR anchors, completion time, project, iteration, requirement, test task, and idempotency key. Write these fields as `oneos.test-deployment/v1` in the test task and read them back. Pipeline submission alone, running/unknown status, or a deployment that does not contain the merged version blocks handoff.
32. Only after relation, owner, description, iteration, and test-deployment gates pass may the separate requirement transition `开发完成 → 待测试` be performed and verified. Emit the formal handoff with the exact iteration and deployment evidence, followed by `/skill YunxiaoQA` and `开始测试：测试任务=<测试任务编号>；需求=<需求编号>`; do not fabricate a test result.
33. For `修复bug:<BUG-ID>`, resolve the exact Bug and require a developer-actionable non-terminal state; the Bug owner may be any user and must not be reassigned implicitly. Read formal association items, requirement, development-task, failed-case, and repository relations when present, but allow zero association items and no repository metadata. Resolve the target codebase from the active workspace, Bug description, reproduction path, page URL or interface, runtime evidence, and current conversation. Stop before code writes only when reproduction input, repair scope, or target environment is missing, or conflicting evidence makes the modification target unsafe. The developer must not read the creator merely to derive a verifier and must never change `验证人/验证者`.
34. Select the repair branch independently for every affected repository. When the Bug has association items, follow their formal relations to the underlying requirement, then inspect that requirement and its development tasks for a remotely existing, writable, safely synchronizable development branch formally associated with the same repository. Reuse it only when exactly one valid branch is resolved. When no valid branch is found, the result is ambiguous, or the Bug has no association items, create or reuse `fix/<BUG-ID>` from the repository's verified actual integration branch. Never choose a branch by title/name resemblance alone. Associate the selected branch and later MR with the Bug itself, and retain independently proven requirement/development-task/failed-case relations without fabricating missing ones.
35. Reproduce the Bug, implement the smallest in-scope fix, and verify the failing path, boundaries, and adjacent paths. Keep the same single-Bug node active while fetching latest code, rerunning scoped verification, committing, pushing, opening or reusing the MR, and immediately attempting a platform-permitted merge to the verified integration branch. Do not inspect or wait for review approval, CI status, or discussion resolution; self-approval is allowed but optional. Code conflicts, a wrong target branch, a technically non-mergeable MR, or a platform rejection still stop that Bug without bypassing protection.
36. Coordinate or verify one test deployment for the single Bug without modifying production pipelines. Only after the deployed test version is proven, set the Bug to `已修复` and read back its status before handing it to `YunxiaoQA`. Do not write or gate on `验证人/验证者`; that field is owned by `YunxiaoQA` when the Bug is created. Never close it or write a passing retest.
37. For `/go 修复负责人是我的所有Bug`, first run `skill-run yunxiao_cli_bug_batch.py doctor --require-auth`, then `snapshot --space-id <精确项目ID>...`. Resolve each Bug's exact repository and branch by step 34, group by exact repository plus target branch, and create `oneos.yunxiao-cli-bug-delivery-plan/v1`. Run `skill-run yunxiao_cli_bug_delivery.py preflight --plan <计划JSON>` before code writes. The preflight must prove Codeup IDs/permissions/branches, one exact test Flow, its repository/branch mapping, and one declared execution mode. `manual-cli` is forbidden when an automatic target-branch trigger exists; `auto-after-merge` requires exactly one relevant trigger event. Do not use browser Cookie or DOM writes when any CLI, authentication, project, Codeup, or Flow gate fails.
38. Run `ensure-branches --preflight <回执>` so Codeup branch creation/reuse and read-back occur through CLI. Then loop through processable Bugs: use `yunxiao_cli_bug_batch.py set-status` when the live state must enter the real in-progress state, edit and validate locally, and record per-Bug diff boundaries. Do not commit, push, create an MR, merge, or deploy inside the loop. Group workspaces by exact repository plus selected target branch and never mix unrelated pre-existing changes.
39. After the last processable Bug passes local validation, rerun combined checks and reconcile each group. Create at most one local commit and one native `git push` per group, then write the group-to-remote-commit map. Run `ensure-mrs --branches <回执> --commit-map <映射>` and `merge-mrs --mrs <回执>` so Codeup MR creation, Bug association, merge, and `mergedRevision` read-back all use CLI. Finally run `start-test-pipeline --merges <回执>` exactly once: manual mode starts one Flow run; automatic mode starts none and attaches only to the unique post-baseline run containing every merged revision. Any failed group, zero automatic run, or multiple matching runs blocks status completion and never causes a compensating second deployment.
40. Run `check-test-pipeline --run <回执>` until terminal. Only a successful Flow run whose source proves every merged revision may generate `oneos.test-deployment/v1`. Pass that file to `yunxiao_cli_bug_batch.py set-status --snapshot <快照文件> --target 已修复 --deployment-evidence <证据文件> --serial <BUG-ID>...`. The adapter updates only `status`, then exactly re-reads serial, status, owner, and verifier. A per-Bug status failure blocks only that Bug; never repeat submission or test deployment. Preserve per-Bug operations and attribution although commit/MR/deployment evidence is shared.
41. For `处理发布回流：发版任务=<ID>`, execute `references/test-deployment-handoff.md`: verify the release incident and rollback/acceptance evidence, require the QA-created Bug set, reuse the consolidated Bug repair path, deploy once to test, and emit `验证发布回流`; never start production or skip QA retest.
42. Before the final response for `分配任务`, `开发任务`, batch development, `完成开发`, single-Bug repair, batch Bug repair, or release repair, execute `references/change-reporting.md`. Record repository baselines before writes, derive file lists from live Git evidence, distinguish planned from actual changes, and emit both `实际执行操作` and `实际代码变更` even when blocked. Do not report a node or batch complete when these sections are missing.
43. For `清理分支：发版任务=<ID>`, execute `references/release-branch-cleanup.md`. Re-read the release task, require state=`已完成`, validate the product-acceptance evidence and immutable production anchor, derive candidates from trusted task/Bug/MR relations, apply retention and per-branch safety gates, delete eligible exact remote branches with read-back, and perform only safe current-machine local cleanup. Never change the release, requirement, task, or Bug state. Treat already-absent branches as idempotent success and report other developers' local branches as requiring the same command on their machines.

## Non-negotiable gates

- Labels are module metadata, never development identity.
- Use the `【开发】` prefix when creating development children and for batch discovery, but do not require that prefix or a child-task type when an explicit `开发任务:任务=<ID>` is invoked.
- Every command has a precondition gate. On failure, perform no state-changing action and return the failed check, live value, expected value, impact, and exact remediation or next command.
- Batch execution may continue past a failed task but may not continue that task past its failed gate.
- Bug batch execution may continue past a failed Bug but may not continue that Bug past its failed gate.
- Freeze the batch task list before implementation. Do not silently add tasks assigned during the run.
- Use an isolated worktree or equivalent workspace for every batch task; never mix unsubmitted changes from different tasks.
- For Bug batches, group worktrees by exact repository plus selected target branch. Multiple frozen Bugs may intentionally share one group only when their diff boundaries remain auditable; never mix a development task, an unrelated Bug, or pre-existing user changes into that workspace.
- Do not mark the batch goal complete while any snapshot task remains unimplemented or blocked.
- In `分配任务`, `任务=<ID>` always identifies the source `【交付】` task, never the child development task.
- `分配任务` must use `yunxiao_cli_allocate_task.py` through official `aliyun devops` CLI for every Yunxiao read and write. Missing CLI/plugin/PAT/organization ID, a changed preflight fingerprint, or an ambiguous create-time owner is a zero-write blocker; never fall back to browser/DOM/Cookie operations or expose credentials.
- Never reassign the `【交付】` task from 何斐 or overwrite its planned dates or estimated hours. This Skill owns only `待处理 → 已分配 → 处理中`; `处理中→已完成` belongs to post-release product acceptance in `YunxiaoPM`.
- If a referenced `【交付】` is already `已完成`, do not create/reopen development or test children and do not roll any state back. A new post-acceptance change must return to `YunxiaoPM` for a new requirement/delivery lifecycle.
- Allocation must attempt both `TASK_SUB→【交付】` and `ASSOCIATED→需求`, but missing relations are not a `开发任务` or `完成开发` gate; derive the source scope from task and project evidence and report the missing traceability.
- The managed next-stage description block is idempotent and must not overwrite human-authored description content.
- Derive type, scope, target project, repository, and actual integration branch automatically from requirement, task, project, Codeup, runtime, and workspace evidence. Never require repository addresses from the conversation.
- `/go 开发任务` accepts only `任务=<开发任务编号>` plus the optional literal suffix `输出执行方案`. Do not require or encourage `类型=`、`仓库=`、`前端仓库=`、`后端仓库=`、`范围=` or `基线=`.
- Plan mode is read-only until explicit same-task confirmation. Keep the goal unfinished while waiting; do not mark it complete or blocked merely because confirmation is pending.
- Direct mode skips plan presentation and confirmation only. It never skips requirement/material, state, repository, implementation, or verification gates.
- Re-read plan inputs before executing a confirmed plan. Any execution-relevant change invalidates the confirmation and requires a revised plan.
- Plan mode must label its operation and code sections as planned and unexecuted. After confirmation, replace them with actual evidence; never present a proposal as completed work.
- Every write-capable node must report `实际执行操作` and `实际代码变更`. Use Git status/diff/commit/MR evidence and include every task-owned added, modified, deleted, or renamed file with behavior, reason, line counts, and verification.
- Record the pre-write repository baseline and exclude unrelated pre-existing dirty files. Never claim another task's or the user's existing changes.
- Batch development and batch Bug repair must repeat the operation ledger and code inventory for every item. Aggregate counts never replace per-item details.
- A blocked node must still report completed operations, current task-owned differences, unexecuted actions, retained worktree/branch, and continuation condition.
- If no code changed, write `代码变更：无` with an evidence-backed reason. Do not claim a code implementation or code-defect repair complete without code changes unless the proven resolution is configuration, data, environment, or genuinely no-code.
- Prefer frontend=`develop` and backend=`dev`, but their absence is not a gate; use the repository's verified actual integration branch.
- Missing or failed branch-association automation is not a gate. Record whether state changes were native, bridged, or direct.
- An optimization requirement with empty, unreadable, placeholder, or ambiguous description must stop with specific missing information.
- A new requirement without attachments, without a detailed requirement document, without a local HTML prototype, without an accessible prototype URL, or with conflicting local/online prototypes must stop with evidence.
- A development task cannot complete without proportionate developer-side automated and real-page verification against the implemented version. This evidence is not a formal QA plan, case execution, report, or acceptance result.
- `/go 完成开发` must run a fresh developer-side completion validation rather than reusing the first validation record.
- Developer-discovered failures remain inside the development scope; formal Bug creation, retest, closure, and test evidence follow `YunxiaoQA` after test handoff.
- Creating or reusing `【测试】` and moving the requirement `开发完成 → 待测试` are two separate verified actions. The test task must be a formal `TASK_SUB` child of the exact source `【交付】` task and `ASSOCIATED` with the source requirement. These two relation IDs, exactly one project `测试主管`, owner-role equality, and the managed description are mandatory read-back gates.
- Normal requirements, not only Bug fixes, must be deployed to test before `开发完成 → 待测试`. Exactly one iteration and a read-back `oneos.test-deployment/v1` block covering the merged version are mandatory; pipeline submission or local validation is insufficient.
- Never leave a newly created test task at project top level. A reusable top-level test task may be attached only when its requirement and delivery are unambiguous; never detach or silently reparent a task from another delivery tree.
- The managed `## 开发交接` block is idempotent and must preserve human-authored description outside it. Never fabricate temporary requirement changes; an acceptance-affecting change without explicit confirmation blocks handoff.
- Development may mark a Bug `已修复` but may not close it or write a passing retest result; only `YunxiaoQA` may do so from retest evidence.
- Planned dates and estimated hours are scheduling data; they do not prove real development start.
- YunxiaoPM is the only product-stage entry. This Skill must not accept `已确认` or `设计完成` as development intake.
- A YunxiaoPM handoff intentionally has no `【开发】` or `【测试】` task. Their absence is not a handoff failure.
- Never create a second `【交付】` task or recreate missing analysis/design tasks during development intake.
- A fast-track or number-push handoff may legitimately have no analysis task or no design task.
- A placeholder `【交付】` description is an explicit product risk, not proof that design is complete.
- A commit does not prove development completion. Review approval, CI status, and discussion resolution are intentionally not merge gates. An MR may be merged only to the verified actual integration branch when it is conflict-free, technically mergeable, and accepted by Codeup under current permissions and protection settings.
- Requirement and development-task association for branches and MRs is best-effort. Attempt it for every applicable repository, record the outcome, and continue when unsupported or unsuccessful.
- Self-approval of the current account's own MR is allowed when Codeup permits it, but the Skill does not require approval before attempting merge.
- A requirement involving one repository must not wait for an explicitly non-applicable repository; a multi-repository requirement must not finish early.
- `已修复` means ready for retest, not closed.
- The canonical single-Bug command is exactly `修复bug:<BUG-ID>` after `/skill yunxiao-development-delivery`; it replaces both legacy `接收Bug` and `Bug修复完成` commands.
- The canonical Bug batch command is `/go 修复负责人是我的所有Bug` after `/skill yunxiao-development-delivery`. Accept close semantic equivalents, but always freeze and display the list; do not invoke the end-to-end single-Bug submit/deploy handler inside the loop.
- A single-Bug command may repair a Bug owned by any user. Never reassign it implicitly; preserve and report the live owner.
- A Bug may have zero association items and no repository information. Neither condition is a repair gate. With associations, follow formal relations to the requirement and reuse its uniquely verified development branch when available; otherwise create `fix/<BUG-ID>` from the verified integration branch. Always associate new branch/MR assets with the Bug itself and stop only if conflicting evidence leaves the modification target unsafe to determine.
- Development must never set, clear, replace, or gate completion on a Bug's `验证人/验证者`. `YunxiaoQA` sets that field to the current test user when the Bug is created; development preserves it through single and batch repair.
- Bug batches must perform zero commits, pushes, MRs, merges, or deployments during the per-Bug edit loop. Submit at most once per repository-and-branch group after the loop and trigger exactly one compatible test deployment for the entire batch.
- The Bug batch must use the bundled official CLI adapters for current-user resolution, Bug snapshot/status/read-back, Codeup repository/branch/MR/merge operations, and Flow run/evidence operations. Missing CLI/plugin/PAT/organization-or-endpoint/project IDs, ambiguous Codeup identity, unsafe trigger configuration, or pipeline/revision mismatch is a global preflight blocker. Never print the PAT or other secrets, pass them as command arguments, store them in plans/receipts/Skill files, or silently fall back to browser/Cookie writes.
- No development or Bug command requires conversation-supplied repository addresses; determine target projects automatically from the work item and code/runtime evidence.
- `清理分支` requires one exact `发版任务` ID, live state=`已完成`, and valid passing `oneos.product-acceptance/v1` evidence consistent across the release task, in-scope requirements, and source delivery tasks. State=`发布完成` means product acceptance is still pending and must produce zero deletions. Release failure, failed/missing/inconsistent acceptance evidence, rollback/uncertainty, missing immutable production anchor, ambiguous scope, insufficient relation/MR proof, or unmet retention keeps the affected branch and reports why.
- Branch names are discovery hints, never deletion proof. Never delete default, protected, integration, or long-lived branches; never use wildcard deletion, force push, `git branch -D`, administrator bypass, or protection-rule changes.
- Remote cleanup and local cleanup are separate. This Skill may clean current Codeup remotes and safe local branches only on the machine where it runs; it cannot delete branches on another developer's computer.
- Do not set a Bug to `已修复` without code verification, MR evidence, and proof that the test environment contains the fixed version. Do not close a Bug; retest and closure belong to `YunxiaoQA`.
- Do not set a development task to `已完成` until `实际完成时间` and `实际开发工时` have been written and read back for that exact task.
- Use the latest applicable MR `merged_at` as `实际完成时间`; do not use the command execution time, first commit time, or first MR merge time when multiple repositories apply.
- Count only Codex tasks or per-item segments with an exact, auditable relation to the development task. Deduplicate by Codex task ID plus segment ID and never assign an unsegmented multi-task conversation in full to more than one development task.
- Sum raw active elapsed seconds first, then round once to minutes. Convert with `实际开发工时 = 总分钟数 ÷ 60`, written to two decimal hours using half-up rounding. Preserve the integer minutes and unrounded calculation in evidence.
- If active elapsed duration, association evidence, field precision, or writeback cannot be verified, stop before task completion. Never substitute first-message-to-last-message wall-clock duration or planned hours.
- Every generated next-stage command must start with an explicit `/skill <skill-name>` selector.
- Never modify production pipelines from this skill.
- A missing CLI/plugin/PAT/organization-or-endpoint capability is a zero-write blocker. It never authorizes visual or browser fallback.

## Return

```text
执行结论：完成|部分完成|阻塞|仅输出方案
项目/迭代：
需求/交付任务/开发任务：
测试任务/父交付任务/关联需求：
负责人/计划开始/计划完成/预计工时：
真实开始时间：
实际完成时间：
Codex关联任务/分段：
Codex总时长（分钟）：
实际开发工时（小时）：
仓库/分支/MR：
Bug负责人/状态：
批量提交组/test部署执行ID：
发版任务/生产版本锚点：
分支清理结果（远程/本机/其他开发机待处理）：
状态变化：
实际执行操作：
1. <系统> <对象> <操作> <变更前→变更后> <结果/证据>
实际代码变更：
- <仓库>/<分支> [新增|修改|删除|重命名] <文件> <代码位置> <修改内容和原因> <+N/-N> <验证>
未执行操作及原因：
门禁结果：
验证：
开发验证/剩余阻塞：
测试建议：
临时需求变更点：
未完成仓库或阻塞：
下一责任角色：
下一条口令：
```
