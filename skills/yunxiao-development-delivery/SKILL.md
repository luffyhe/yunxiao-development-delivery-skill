---
name: yunxiao-development-delivery
description: "Manage Yunxiao development after a YunxiaoPMapp handoff: allocate 【开发】 children, associate them with requirements, run gated `/go 开始开发` implementation, and run `/go 完成开发` through validation, direct platform-permitted merge, actual completion-time capture, and Codex conversation-duration conversion into actual development hours. Execute single or batched Bug repair and stable batch development. Use for 接收产品交棒、分配任务、开始开发、批量实现、完成开发、实际完成时间、实际开发工时、修复Bug、批量修复本人Bug、提交代码、创建分支、创建或合并MR and development-flow diagnosis. In 分配任务, `任务=ID` is the source 【交付】 task; in 开始开发 and 完成开发, it is the 【开发】 child."
---

# Yunxiao Development Delivery

Operate development tasks and Codeup assets without using code activity as a substitute for real work state. Suite version: `7.6.0`.

## Load the required references

Read each selected file completely before acting:

- Development task, Codeup, stage-task and OneOS controls: [references/controls.md](references/controls.md).
- Short Chinese commands and defect-fix workflow: [references/commands.md](references/commands.md).
- `/go 开始开发`, 新增/优化材料门禁, prototype comparison, and implementation completion: [references/implementation-materials.md](references/implementation-materials.md).
- Codex task association, active-duration accounting, minute-to-hour conversion, and completion-field writeback: [references/codex-time-accounting.md](references/codex-time-accounting.md).
- Batch `/go` discovery, stable snapshots, per-task continuation, worktree isolation, and final reporting: [references/batch-execution.md](references/batch-execution.md).
- YunxiaoPMapp handoff input, idempotency, and downstream rotation: [references/yunxiaopmapp-handoff.md](references/yunxiaopmapp-handoff.md).
- Authorization, live-change safety, evidence, and cross-skill handoff: [references/safety-handoff.md](references/safety-handoff.md).
- For browser-driven Yunxiao work, read the stable-session, batched-write, and delayed-readback procedure: [references/browser-execution-efficiency.md](references/browser-execution-efficiency.md).

The safeguards in this Skill are self-contained. If `git-submit-safety` is also installed, use it as an additional repository-specific guardrail.

## Own only the development boundary

Own these outcomes:

1. Accept a verified YunxiaoPMapp handoff whose requirement is already `待开发`.
2. Allocate one or more `【开发】` child tasks with developer, planned dates, and estimated hours, then move the source `【交付】` task from `待处理` to `已分配`.
3. Record the developer's real start and move the development child, source `【交付】` task, and requirement into development.
4. Create branches, commits, and merge requests, and attempt requirement/development-task association without making association success a gate.
5. In `完成开发`, run a second exact-name validation for new requirements, close scoped Bugs, submit and merge all relevant MRs without waiting for review, CI, or discussion state, then write the development task's actual completion time and Codex-derived actual development hours before marking it complete.
6. Use one `修复bug:<BUG-ID>` node to inspect, reproduce, fix, verify, submit, deploy to test, and set the exact defect to `已修复` for tester verification.
7. Create or reuse the unique `【测试】` task, assign it to the uniquely resolved project user with role `测试主管`, move the requirement from `开发完成` to `待测试`, and produce the formal test handoff.
8. For a new requirement, keep the same `/go 开始开发` goal open while `$yunxiao-test-management` executes its scoped cases and closes verified defects.
9. Run `/go 实现所有负责人是我的开发任务` as a stable batch that attempts every active assigned development task without letting one task-level blocker abort the remaining queue.
10. Run `/go 修复负责人是我的所有Bug` as a stable batch: freeze the current developer-actionable Bug list, display it, and invoke the same single-Bug handler for every item while isolating per-Bug blockers.

This Skill does not impersonate the tester: delegate case execution, current-run result recording, retest, and Bug closure to `$yunxiao-test-management` inside the same user-visible goal. Test execution must not change the reusable case's lifecycle state. Do not publish production; hand release actions to `$yunxiao-release-operations`.

## Classify authority

- `audit`: inspect code assets, states, and logs only.
- `plan`: prepare tasks, branch/MR plan, or fix plan only.
- `apply`: create or modify exact named development tasks and formal relations.
- `fix`: edit code after root cause and scope are verified.
- `submit`: commit, push, open, or merge an MR only inside an explicitly invoked `/go 完成开发` for the exact development task or `修复bug:<BUG-ID>` for the exact Bug.
- `document`: produce a development handoff or diagnosis report.

Creating a Bug does not authorize a fix. Generic diagnosis or code editing does not authorize submission. Only an explicit `/go 完成开发` grants exact-task submission and a direct platform-permitted merge attempt, while `修复bug:<BUG-ID>` grants the same restricted submission authority only for that Bug's verified repositories and test integration path.

`/go 开始开发` grants `apply + fix` for the exact associated requirement and confirmed repository scope after all gates pass. The development-task batch grants the same authority separately for each task in its initial snapshot. `/go 完成开发` additionally grants `submit + direct merge attempt` for that task's verified repositories and actual integration branches. `修复bug:<BUG-ID>` grants `apply + fix + submit + direct merge attempt + test-deployment coordination` only for the named Bug and its evidence-resolved target codebase; the Bug batch grants that authority separately for each Bug in its frozen snapshot. Review approval, CI result, and discussion resolution are not inspected, awaited, or used as Skill gates. Self-approval is allowed when Codeup exposes it and the current account is permitted to use it, but it is not required. These commands never grant production deployment, force push, administrator bypass, protection-rule disabling, unrelated refactoring, tester impersonation, or Bug closure.

## Execute

1. For development-task commands, resolve the exact project, requirement, numbered `【交付】` task, development task, repository, and real integration branch. For Bug commands, resolve the exact Bug and project first; Bug relations and repository fields are optional inputs.
2. Re-read the live requirement and `【交付】` task using the explicit YunxiaoPMapp identifiers. Accept only the contract in `references/yunxiaopmapp-handoff.md`; never search or deduplicate by title.
3. For `分配任务`, interpret `任务=<ID>` as the source `【交付】` task. Treat owner resolution as best-effort rather than a gate: set the owner when the supplied value resolves, otherwise keep the existing owner or leave the new task unassigned and report it without stopping task creation. Validate planned start ≤ planned finish. Estimated hours are optional; when supplied, require a positive value.
4. Inspect formal child relations. Create a `【开发】<需求标题>` child when none exists, or reuse the explicitly identified valid child. Set developer, planned start, planned finish, estimated hours, and state `待处理`; create both `TASK_SUB→【交付】` and `ASSOCIATED→需求`, then read both relations back. Only after the child fields, both relations, and the managed next-stage command all pass read-back may the source `【交付】` task move `待处理 → 已分配`. Repeated allocation keeps an already `已分配`、`处理中` or `已完成` delivery task and never rolls it backward.
5. Upsert a managed `## 下一阶段` block in the development task description without overwriting business content. Its executable content is exactly `/skill yunxiao-development-delivery` followed by `/go 开始开发:任务=<开发任务编号>`; never append type, repository, scope, or baseline parameters.
6. Do not require repository information at allocation or from the active conversation. During `开始开发`, analyze the requirement, affected page/interface/data, project configuration, existing code relations, accessible Codeup repositories, and current workspace to determine the applicable frontend/backend project automatically. Missing conversation-supplied repository addresses never block the node; stop only when the evidence itself remains contradictory after discovery and the modification target cannot be made safe.
7. For initial development intake, require the requirement to be `待开发` and the source delivery task to be `已分配`. For a later sibling task, accept requirement=`开发中` and delivery=`处理中` only when the same delivery tree contains verified development-start evidence; for resuming this task, also require its immutable first-start record and formally associated branch. Never change `已确认`/`设计完成` to `待开发` here.
8. For `开始开发`, accept the explicit work-item ID without requiring it to be a `【开发】` child. Prefer a direct requirement relation, then derive the source requirement and scope from the task parent, title, description, attachments, project/iteration context, existing code assets, and repository facts. Missing `TASK_SUB` or `ASSOCIATED` relations alone never block execution. Derive `新增` or `优化` from the resolved requirement/task title, infer `前端`、`后端` or `全栈`, and list the continuous execution tasks before writing.
9. Run the complete pre-write material gate in `references/implementation-materials.md`. For 优化, require a complete and implementable requirement description. For 新增, require downloaded attachments containing the detailed requirement and HTML prototype plus an accessible prototype URL in the requirement description; compare both prototypes and stop on material differences.
10. Only after material gates pass, use the developer's explicit start action as the authoritative start time. Persist the first real start timestamp once in a dedicated field when available; otherwise write a structured task comment. Never replace it with branch or commit time and never overwrite it on retry.
11. After the target project is automatically determined, inspect its real repository configuration and integration/default branches. Prefer frontend=`develop` and backend=`dev` when they exist, but absence of either name is not a gate; use the repository's verified actual integration branch and record the choice. Never create a branch name merely to satisfy this Skill.
12. Prefer `feature/<WORK-ITEM-ID>` or `fix/<BUG-ID>`. For every applicable repository, attempt to associate code assets with the requirement and development task. If either association is unsupported, unavailable, ambiguous, or fails read-back, record the result and continue; association success is not a branch, MR, merge, or completion gate. Defect fixes must still associate the Bug itself when Codeup supports that relation.
13. After the branch is created or reused, try native automation for `开发任务：待处理→处理中` and, for the first started child in the delivery tree, `【交付】任务：已分配→处理中` plus `产品需求：待开发→开发中`. Missing, disabled, or failed automation is not a gate: continue implementation and perform the same authorized state update directly or through the configured bridge, recording the actual method and result instead of claiming native automation passed. A later sibling starts only its own development task and does not repeat the parent or requirement transition.
14. Load `$apply-oneos-v2-frontend-guidelines` for frontend scope and `$alibaba-java-backend-guidelines` for Java backend scope. Inspect repository facts before editing, implement the validated material, and run proportionate automated and real-page verification. Do not treat source inspection as functional or visual verification.
15. For a new requirement, invoke `$yunxiao-test-management` after implementation. Resolve the requirement by the development task's formal relation, then locate validation cases in the same project and iteration by exact requirement name. Execute all exact-name matches, deduplicate/create Bugs titled `[<开发任务ID>]<Bug描述>`, fix them here, and return each `已修复` Bug to testing for retest. Repeat until all matched cases pass and there are no scoped Bugs or every scoped Bug is tester-closed.
16. `/go 开始开发` completes at verified implementation and task evidence for optimization requirements; for new requirements it additionally requires the complete test/defect closure gate in `references/implementation-materials.md`. Do not count Bugs from other requirements.
17. When `开始开发` passes, write a managed next-stage block containing `/skill yunxiao-development-delivery` and `/go 完成开发:任务=<开发任务编号>`. Do not commit, push, create an MR, merge, or deploy during `开始开发`.
18. For a batch `/go`, execute `references/batch-execution.md`: resolve the current account, freeze and display the active task snapshot, call this same single-task handler sequentially in isolated worktrees, record per-task active-duration segments and stops, and continue. A task-level stop never authorizes bypassing its gate.
19. For `/go 完成开发`, inspect the matching `开始开发` evidence when present, but do not use missing or incomplete start-node evidence as a gate. Execute any still-missing material analysis, implementation, first validation, or start-state work inside the same completion goal before submission. For a new requirement, still create an independent completion validation run and loop fix/retest until no scoped Bug exists or every scoped Bug is tester-closed.
20. After completion validation passes, fetch/pull first, stop on code conflicts, rerun the Skill's own scoped verification, then commit, push, and create or reuse MRs for every applicable repository. Attempt to associate each MR with the requirement and development task; record `associated` or `skipped/failed` per relation and continue either way.
21. Do not inspect or wait for Codeup review approval, CI status, or discussion resolution. After MR creation, immediately attempt merge to the repository's verified actual integration branch. Self-approval is allowed but optional. Merge only when the target branch is correct, the MR has no code conflict, Codeup reports it technically mergeable, and the platform accepts the operation under current permissions and protection settings. If Codeup rejects the merge, report the exact platform response; never force push, use administrator bypass, or disable protection rules.
22. After every applicable MR for the exact development task is merged, execute `references/codex-time-accounting.md`. Set `实际完成时间` to the latest verified applicable-MR merge timestamp, converted to the Yunxiao project's timezone. Discover every uniquely associated Codex task or per-item batch segment, sum platform-reported active elapsed seconds, round the aggregate once to whole minutes, convert minutes to decimal hours, and write `实际开发工时`.
23. Read back `实际完成时间` and `实际开发工时`, persist the Codex task IDs/segments, total minutes, conversion expression, written hours, source timestamps, and rounding evidence, then move the exact development task to `已完成`. Do not mark it complete when any source is missing, duplicated, mixed across work items without segmentation, based only on wall-clock span, or rejected by field precision. The source delivery task remains `处理中` while any non-cancelled development child is unfinished.
24. Verify every non-cancelled development task under the delivery tree is `已完成` and has its own read-back actual completion/time-accounting evidence. Only then move the source `【交付】` task `处理中 → 已完成` and the requirement `开发中 → 开发完成`, and read both back. Historical tasks missing either field require an evidence-backed backfill; never copy the current task's time or hours to a sibling.
25. Create or reuse exactly one `【测试】` task. Assign the project `测试主管` when exactly one user is available; otherwise preserve an existing valid owner or leave a new task unassigned, report the zero/multiple-candidate result, and continue without treating it as a gate.
26. Only after the test task gate passes, perform and verify the separate requirement transition `开发完成 → 待测试`. Do not treat test-task creation as proof of the status transition and do not silently emulate failed automation.
27. Emit a formal test handoff whose next command includes `/skill yunxiao-test-management`; do not fabricate a test result.
25. For `修复bug:<BUG-ID>`, resolve the exact Bug and require only a developer-actionable non-terminal state; the Bug owner may be any user and must not be reassigned implicitly. Read requirement, development-task, failed-case, and repository relations when present, but allow zero association items and no repository metadata. Resolve the target codebase from the active workspace, Bug description, reproduction path, page URL or interface, runtime evidence, and current conversation. Stop before writes only when reproduction input, repair scope, or target environment is missing, or when conflicting evidence makes the modification target unsafe to determine.
26. Reproduce the Bug, determine the evidence-backed root cause, create or reuse `fix/<BUG-ID>` from the resolved frontend `develop` or backend `dev`, and formally associate the branch/MR with the Bug itself. Preserve and use requirement, development-task, and failed-case relations only when they already exist or are independently proven; never fabricate them and never require them for a standalone Bug. Implement the smallest in-scope fix and verify the failing path, boundaries, and adjacent paths.
27. Keep the same single-Bug node active while fetching latest code, rerunning scoped verification, committing, pushing, opening or reusing the MR, and immediately attempting a platform-permitted merge to the verified integration branch. Do not inspect or wait for review approval, CI status, or discussion resolution; self-approval is allowed but optional. Code conflicts, a wrong target branch, a technically non-mergeable MR, or a platform rejection still stop that Bug without bypassing protection. Coordinate or verify test deployment without modifying production pipelines. Only after the deployed test version is proven may development set the Bug to `已修复` and hand it to `$yunxiao-test-management`; never close it or write a passing retest.
28. For `/go 修复负责人是我的所有Bug`, resolve the current account ID, freeze and display all Bugs assigned to that account whose live workflow state requires developer action, and exclude deleted, archived, cancelled, closed, or `已修复`/waiting-for-retest items. Invoke `修复bug:<BUG-ID>` sequentially in isolated worktrees; a per-Bug blocker stops only that Bug, is recorded, and does not abort the remaining list.

## Non-negotiable gates

- Labels are module metadata, never development identity.
- Use the `【开发】` prefix when creating development children and for batch discovery, but do not require that prefix or a child-task type when an explicit `开始开发:任务=<ID>` is invoked.
- Every command has a precondition gate. On failure, perform no state-changing action and return the failed check, live value, expected value, impact, and exact remediation or next command.
- Batch execution may continue past a failed task but may not continue that task past its failed gate.
- Bug batch execution may continue past a failed Bug but may not continue that Bug past its failed gate.
- Freeze the batch task list before implementation. Do not silently add tasks assigned during the run.
- Use an isolated worktree or equivalent workspace for every batch task; never mix unsubmitted changes from different tasks.
- Use an isolated worktree or equivalent workspace for every batched Bug; never mix unsubmitted changes from different Bugs or development tasks.
- Do not mark the batch goal complete while any snapshot task remains unimplemented or blocked.
- In `分配任务`, `任务=<ID>` always identifies the source `【交付】` task, never the child development task.
- Never reassign the `【交付】` task from 何斐 or overwrite its planned dates or estimated hours. This Skill owns only its exact status path `待处理 → 已分配 → 处理中 → 已完成`, after the corresponding allocation, first-start, and all-children-complete gates pass.
- Allocation must attempt both `TASK_SUB→【交付】` and `ASSOCIATED→需求`, but missing relations are not a `开始开发` or `完成开发` gate; derive the source scope from task and project evidence and report the missing traceability.
- The managed next-stage description block is idempotent and must not overwrite human-authored description content.
- Derive type, scope, target project, repository, and actual integration branch automatically from requirement, task, project, Codeup, runtime, and workspace evidence. Never require repository addresses from the conversation.
- `/go 开始开发` accepts only `任务=<开发任务编号>` as its business parameter. Do not require or encourage `类型=`、`仓库=`、`前端仓库=`、`后端仓库=`、`范围=` or `基线=`.
- Prefer frontend=`develop` and backend=`dev`, but their absence is not a gate; use the repository's verified actual integration branch.
- Missing or failed branch-association automation is not a gate. Record whether state changes were native, bridged, or direct.
- An optimization requirement with empty, unreadable, placeholder, or ambiguous description must stop with specific missing information.
- A new requirement without attachments, without a detailed requirement document, without a local HTML prototype, without an accessible prototype URL, or with conflicting local/online prototypes must stop with evidence.
- A new requirement cannot complete `/go 开始开发` without at least one exact-name validation case in the same project and iteration, zero unexecuted/blocked/failed cases, retest evidence for every historical failure, and zero active or fixed-unretested scoped Bugs.
- A new requirement cannot complete `/go 完成开发` by reusing the `开始开发` test record. It must run the exact-name validation cases again in a new execution record and end with no scoped Bug or all scoped Bugs tester-closed.
- Bugs created by `开始开发` or `完成开发` validation must be titled `[<开发任务ID>]<Bug描述>` and formally associated with the requirement, development task, and failed case.
- Creating or reusing `【测试】` and moving the requirement `开发完成 → 待测试` are two separate verified actions. Test-supervisor assignment is best-effort and never blocks either action.
- Development may mark a Bug `已修复` but may not close it or write a passing retest result; only `$yunxiao-test-management` may do so from retest evidence. Neither skill changes the reusable case's lifecycle state merely because it was executed.
- Planned dates and estimated hours are scheduling data; they do not prove real development start.
- YunxiaoPMapp is the only product-stage entry. This Skill must not accept `已确认` or `设计完成` as development intake.
- A YunxiaoPMapp handoff intentionally has no `【开发】` or `【测试】` task. Their absence is not a handoff failure.
- Never create a second `【交付】` task or recreate missing analysis/design tasks during development intake.
- A fast-track or number-push handoff may legitimately have no analysis task or no design task.
- A placeholder `【交付】` description is an explicit product risk, not proof that design is complete.
- A commit does not prove development completion. Review approval, CI status, and discussion resolution are intentionally not merge gates. An MR may be merged only to the verified actual integration branch when it is conflict-free, technically mergeable, and accepted by Codeup under current permissions and protection settings.
- Requirement and development-task association for branches and MRs is best-effort. Attempt it for every applicable repository, record the outcome, and continue when unsupported or unsuccessful.
- Self-approval of the current account's own MR is allowed when Codeup permits it, but the Skill does not require approval before attempting merge.
- A requirement involving one repository must not wait for an explicitly non-applicable repository; a multi-repository requirement must not finish early.
- `已修复` means ready for retest, not closed.
- The canonical single-Bug command is exactly `修复bug:<BUG-ID>` after `/skill yunxiao-development-delivery`; it replaces both legacy `接收Bug` and `Bug修复完成` commands.
- The canonical Bug batch command is `/go 修复负责人是我的所有Bug` after `/skill yunxiao-development-delivery`. Accept close semantic equivalents, but always freeze and display the list before invoking the single-Bug handler.
- A single-Bug command may repair a Bug owned by any user. Never reassign it implicitly; preserve and report the live owner.
- A Bug may have zero association items and no repository information. Neither condition is a repair gate. Use existing relations when present, resolve the target codebase from code and runtime evidence, associate new branch/MR assets with the Bug itself, and stop only if conflicting evidence leaves the modification target unsafe to determine.
- No development or Bug command requires conversation-supplied repository addresses; determine target projects automatically from the work item and code/runtime evidence.
- Do not set a Bug to `已修复` without code verification, MR evidence, and proof that the test environment contains the fixed version. Do not close a Bug; retest and closure belong to `$yunxiao-test-management`.
- Do not set a development task to `已完成` until `实际完成时间` and `实际开发工时` have been written and read back for that exact task.
- Use the latest applicable MR `merged_at` as `实际完成时间`; do not use the command execution time, first commit time, or first MR merge time when multiple repositories apply.
- Count only Codex tasks or per-item segments with an exact, auditable relation to the development task. Deduplicate by Codex task ID plus segment ID and never assign an unsegmented multi-task conversation in full to more than one development task.
- Sum raw active elapsed seconds first, then round once to minutes. Convert with `实际开发工时 = 总分钟数 ÷ 60`, written to two decimal hours using half-up rounding. Preserve the integer minutes and unrounded calculation in evidence.
- If active elapsed duration, association evidence, field precision, or writeback cannot be verified, stop before task completion. Never substitute first-message-to-last-message wall-clock duration or planned hours.
- Every generated next-stage command must start with an explicit `/skill <skill-name>` selector.
- Never modify production pipelines from this skill.

## Return

```text
项目/迭代：
需求/交付任务/开发任务：
负责人/计划开始/计划完成/预计工时：
真实开始时间：
实际完成时间：
Codex关联任务/分段：
Codex总时长（分钟）：
实际开发工时（小时）：
仓库/分支/MR：
状态变化：
门禁结果：
验证：
用例/Bug闭环：
未完成仓库或阻塞：
下一责任角色：
下一条口令：
```
