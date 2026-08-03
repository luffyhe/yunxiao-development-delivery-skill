# 云效 CLI 统一执行运行时

本 Skill 中所有云效 Projex、Codeup、Flow 和 AppStack 的读取、写入、日志查询与结果回读都必须使用官方 `aliyun devops` CLI。禁止使用浏览器、视觉点选、截图/OCR、DOM、Cookie、连接器或网页内部接口；CLI 失败时停止并报告缺失能力，不得切换执行通道。

## 环境

CLI 只从 `PATH`、`ALIYUN_CLI_PATH` 或官方默认安装位置发现。认证只读取以下本机环境变量，不在参数、计划、回执、日志、Skill 或聊天中记录其值：

- `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN`
- 中心版：`ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID`
- Region 版：`ALIBABA_CLOUD_YUNXIAO_API_BASE_URL`

先执行：

```text
skill-run yunxiao_cli_gateway.py doctor
```

## 适配器选择

1. `分配任务`使用 `yunxiao_cli_allocate_task.py`。
2. 批量 Bug 的 Projex 快照和状态写回使用 `yunxiao_cli_bug_batch.py`，Codeup/Flow 使用 `yunxiao_cli_bug_delivery.py`。
3. 其他接收交棒、开始开发、完成开发、单 Bug、测试任务、发布回流和分支清理的云效动作使用 `yunxiao_cli_gateway.py`。
4. 本地代码读取、编辑、测试、`git commit` 和 `git push`不经过网关；Codeup 远端分支、MR、合并和删除必须经过 CLI 适配器。

## 只读调用

把单个白名单只读请求保存为临时 JSON：

```json
{
  "operation": "projex-get-workitem",
  "args": ["--id", "工作项内部ID"]
}
```

然后执行：

```text
skill-run yunxiao_cli_gateway.py read --request <请求JSON>
```

只读白名单覆盖 `base-get-*` 以及 Projex、Codeup、Flow、AppStack 的 `get/list/search/find` 操作。精确 CLI 参数必须来自当前插件的 `aliyun devops <operation> --help`，不得猜测。

## 写事务

所有未由专用适配器封装的写入都使用 `oneos.yunxiao-cli-transaction-plan/v1`：

```json
{
  "schema": "oneos.yunxiao-cli-transaction-plan/v1",
  "label": "精确业务动作",
  "authority": "apply",
  "idempotencyKey": "稳定业务键",
  "guards": [
    {
      "operation": "projex-get-workitem",
      "args": ["--id", "工作项内部ID"],
      "expect": {"status.displayName": "待处理"}
    }
  ],
  "actions": [
    {
      "operation": "projex-update-workitem",
      "args": ["--id", "工作项内部ID", "--status", "目标状态ID"]
    }
  ],
  "verifications": [
    {
      "operation": "projex-get-workitem",
      "args": ["--id", "工作项内部ID"],
      "expect": {"status.displayName": "处理中"}
    }
  ]
}
```

执行顺序固定为：

```text
skill-run yunxiao_cli_gateway.py preflight --plan <计划JSON> --output <预检回执JSON>
skill-run yunxiao_cli_gateway.py apply --preflight <预检回执JSON> --receipt <执行回执JSON>
```

`apply`重放所有守卫并比较完整 JSON 哈希；发生漂移时零写入。动作只执行一遍，随后只运行计划内定向回读。相同计划指纹已有成功账本时直接返回原回执，不重复写入。动作可在完整参数值中使用 `${action.0.id}` 形式引用前序动作输出；不得在普通字符串中拼接模板。

分支删除还必须使用 `authority=cleanup` 且设置 `destructiveConfirmation=true`。网关拒绝凭据字段和值，不保存敏感流水线参数；敏感参数只能引用 Flow 已配置的受保护变量。

## 性能

- 每条业务命令只运行一次 `doctor`，不要对同一未变化事务执行第二次 `apply`。
- 预检只读取写入门禁所需对象；成功后只回读被写字段、关系、执行或日志。
- 独立的只读发现可并行；任何存在依赖或写入的步骤保持顺序。
- 等待云效最终一致性时使用短间隔定向回读，不重新扫描整个项目。
- 长流水线按不超过 60 秒的节奏轮询并向用户汇报，不使用一次超长阻塞等待。
