# 云效CLI批量Bug端到端适配器

## 1. 适用范围

批量命令中的云效平台动作必须全部通过官方`aliyun devops` CLI执行：

1. 通过PAT解析当前用户；
2. 按精确项目ID查询当前用户负责、需要开发处理的Bug；
3. 并发补读Bug详情、正式关联项和外部代码关系，生成冻结快照；
4. 将快照内明确指定的Bug改为项目真实`处理中`或`已修复`；
5. 每次状态写入后回读编号、状态、负责人和验证者。
6. 查询Codeup代码库、分支和MR；
7. 创建或复用精确分支，创建或复用MR，合并并回读`mergedRevision`；
8. 校验唯一test流水线及其代码源、目标分支和触发方式；
9. 通过CLI启动一次手动流水线，或附着到合并后唯一自动运行实例；
10. 查询流水线终态并证明运行实例包含全部合并版本，再生成部署证据。

代码编辑、编译测试、`git commit`和`git push`是本机Git动作，不属于云效OpenAPI；仍在隔离工作区执行。分支/MR/合并和Flow查询执行属于云效动作，禁止再通过浏览器、DOM或Cookie执行。本文件只定义批量Bug命令；`分配任务`另按`yunxiao-cli-allocation.md`执行。

## 2. CLI和凭证门禁

要求：

- 阿里云CLI可执行；
- 已安装`aliyun-cli-devops`专用插件；
- `aliyun devops version`成功；
- PAT只通过`ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN`提供；
- 中心版设置`ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID`；
- Region版设置`ALIBABA_CLOUD_YUNXIAO_API_BASE_URL`；
- 口令或已验证上下文提供一个或多个精确项目ID。

禁止把PAT写入命令参数、Skill、仓库、快照、日志或聊天。CLI、插件、认证或范围门禁失败时全批停止，不得静默回退浏览器、DOM或Cookie写入。

适配器只能输出仓库、分支、MR和流水线的必要摘要。不得回显流水线完整配置、Webhook、访问签名、下载签名、密码或密钥字段。

## 3. 预检

```text
skill-run yunxiao_cli_bug_batch.py doctor --require-auth
```

只回报CLI版本、插件版本、凭证变量是否存在以及当前用户ID/名称；不输出PAT。

## 4. 冻结快照

```text
skill-run yunxiao_cli_bug_batch.py snapshot --space-id <项目ID> [--space-id <项目ID>]
```

默认可处理状态：`待确认`、`待处理`、`处理中`、`再次打开`、`重新打开`。通过`--actionable-status`可显式覆盖，但不得加入`已修复`、`已关闭`、`已取消`或归档状态。

脚本把完整快照写到系统临时目录，并在标准输出返回快照路径、当前用户、Bug编号/状态/负责人/验证者和耗时。后续状态修改只接受该文件中的Bug；运行期间新分配Bug不得加入。

## 5. Codeup与Flow只读预检

代码写入前生成交付计划JSON：

```json
{
  "schema": "oneos.yunxiao-cli-bug-delivery-plan/v1",
  "snapshotPath": "<冻结快照>",
  "groups": [
    {
      "groupId": "frontend-develop",
      "repositoryId": "6316668",
      "sourceBranch": "fix/ONEOS-123",
      "targetBranch": "develop",
      "bugSerials": ["ONEOS-123"],
      "reuseExisting": false,
      "mrTitle": "fix(ONEOS-123): <摘要>",
      "mrDescription": "<修复和验证摘要>"
    }
  ],
  "testPipeline": {
    "pipelineId": "4754190",
    "expectedName": "oneos-web-test",
    "environment": "test",
    "executionMode": "auto-after-merge",
    "params": {}
  }
}
```

执行：

```text
skill-run yunxiao_cli_bug_delivery.py preflight --plan <计划JSON>
```

预检必须证明：

- 每个Bug来自同一冻结快照且只属于一个提交组；
- Codeup数字仓库ID、读写权限、目标分支和提交基线可回读；
- 已有源分支仅在`reuseExisting=true`且提交一致时复用；
- 流水线ID与名称精确匹配，名称含`test/测试`且不含`prod/生产`；
- 流水线代码源精确覆盖每个仓库和目标分支；
- `executionMode=manual-cli`时目标分支不得已配置自动触发；
- `executionMode=auto-after-merge`时只能有一个相关自动触发事件。若同时存在`push`和`merge_request/merged`，因可能重复发布而阻塞。

预检记录最近一次运行ID作为自动触发基线，输出带哈希的回执。

## 6. 创建或复用Codeup分支

```text
skill-run yunxiao_cli_bug_delivery.py ensure-branches --preflight <预检回执>
```

适配器重新读取目标分支并核对预检提交。目标分支变化时停止并要求重新预检。创建分支后必须回读精确名称和提交；同名分支被其他提交占用时阻塞。

## 7. 进入处理中并循环修改

逐Bug开始修改前，在确有必要时执行：

```text
skill-run yunxiao_cli_bug_batch.py set-status --snapshot <快照文件> --target 处理中 --serial ONEOS-123
```

适配器重新读取Bug，确认编号、负责人和当前状态仍与冻结范围相容；从该Bug真实项目和工作项类型的工作流中解析唯一目标状态ID；只写`status`，然后回读编号、状态、负责人和验证者。已经是`处理中`时按幂等成功返回。

循环内只修改和验证代码，不提交、不push、不创建MR、不合并、不发布。最后一个Bug完成后，每个`仓库+源分支+目标分支`组在本地最多一次commit和一次`git push`。Git push后生成映射JSON：

```json
{
  "frontend-develop": "0123456789abcdef0123456789abcdef01234567"
}
```

## 8. 通过CLI创建并合并MR

```text
skill-run yunxiao_cli_bug_delivery.py ensure-mrs --branches <分支回执> --commit-map <提交映射JSON>
skill-run yunxiao_cli_bug_delivery.py merge-mrs --mrs <MR回执>
```

`ensure-mrs`先回读Codeup源分支，要求远端40位提交ID与本地映射一致；随后按精确仓库、源分支和目标分支复用唯一打开MR，或通过CLI创建MR并用快照内部工作项ID关联Bug。创建后回读`localId`、仓库、源/目标分支、冲突和WIP状态。

`merge-mrs`不读取或等待评审、CI和讨论状态；只在MR精确、非WIP、无冲突且平台接受时合并。合并后必须回读`state=MERGED`和`mergedRevision`。任何组失败都禁止test发布。

## 9. 唯一test流水线

```text
skill-run yunxiao_cli_bug_delivery.py start-test-pipeline --merges <合并回执>
skill-run yunxiao_cli_bug_delivery.py check-test-pipeline --run <运行回执>
```

- `manual-cli`：适配器使用`flow-create-pipeline-run`启动一次，并用确定性回执防止同批重复启动。
- `auto-after-merge`：适配器不再手动启动；只查询预检基线之后的运行实例，并要求恰好一个实例包含全部`mergedRevision`。零个时等待，多于一个时按重复发布阻塞。
- 查询终态使用`flow-get-pipeline-run`。只有`SUCCESS`且运行代码源中包含全部合并版本时生成`oneos.test-deployment/v1`证据；仅“流水线成功”但版本不一致不能标记Bug已修复。

## 10. test发布后标已修复

`check-test-pipeline`生成的部署证据至少包含：

```json
{
  "environment": "test",
  "status": "成功",
  "executionId": "RUN-123",
  "executionUrl": "https://...",
  "deployedVersion": "commit-or-artifact",
  "includedBugSerials": ["ONEOS-123", "ONEOS-124"],
  "commitOrMrAnchors": ["commit-or-mr"]
}
```

调用：

```text
skill-run yunxiao_cli_bug_batch.py set-status --snapshot <快照文件> --target 已修复 --deployment-evidence <证据JSON> --serial ONEOS-123 --serial ONEOS-124
```

证据不是test成功、缺执行ID、缺版本/制品、缺代码锚点或未覆盖全部指定Bug时，零状态写入。写入阶段逐Bug失败隔离；一个Bug失败不重复提交、MR或test发布。

## 11. 输出与续跑

脚本把状态收口回执写到系统临时目录，记录：

- 快照ID和快照哈希；
- Bug编号和内部ID；
- 变更前后状态；
- 负责人和验证者一致性；
- CLI更新及回读结果；
- Codeup分支、远端提交、MR和`mergedRevision`回读；
- Flow执行模式、自动触发基线、唯一运行ID和运行版本校验；
- 部署证据摘要；
- 耗时与错误。

同一目标状态重复执行时，已经达到目标且负责人、验证者一致的Bug按幂等成功返回。分支、MR和合并按精确标识幂等复用；手动流水线回执存在时不得再次启动。快照或回执被修改、Bug不在快照、负责人变化、编号回读不一致、验证者变化、提交漂移或出现多个匹配流水线运行时停止对应阶段。
