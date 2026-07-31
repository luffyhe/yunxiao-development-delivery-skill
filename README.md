# 云效开发交付 Skill

`yunxiao-development-delivery` 用于承接产品需求交棒后的云效开发流程，当前版本为 `8.5.0`。

## 能做什么

- 根据【交付】任务创建并分配【开发】子任务
- 将交付任务推进到“已分配”，衔接“开始开发”
- 创建或复用需求开发分支
- 执行单个开发任务或批量实现本人负责的开发任务
- 修复单个 Bug 或批量修复本人负责的 Bug
- 完成开发时回填实际完成时间和实际开发工时
- 全部开发子任务完成后，将产品需求推进到开发完成并交接测试

## 安装

### Codex

```bash
npx skills add luffyhe/yunxiao-development-delivery-skill --skill yunxiao-development-delivery -a codex -g -y
```

### Cursor

```bash
npx skills add luffyhe/yunxiao-development-delivery-skill --skill yunxiao-development-delivery -a cursor -g -y
```

Codex 与 Cursor 使用同一业务规则源，并分别生成离线包：

- `packages/codex/yunxiao-development-delivery.zip`：包含 Codex UI 元数据。
- `packages/cursor/yunxiao-development-delivery.zip`：不携带 Codex 专用 UI 元数据。
- 两个包的 SHA-256 分别记录在对应目录的 `manifest.json`。

重新构建双版本包：

```powershell
pwsh -File ./tools/build-dual-client-packages.ps1
```

### 同时安装到所有已识别的 Agent

```bash
npx skills add luffyhe/yunxiao-development-delivery-skill --skill yunxiao-development-delivery -a '*' -g -y
```

## 更新

```bash
npx skills update yunxiao-development-delivery -g -y
```

如果本机没有保留原安装来源，重新执行对应安装命令即可安装仓库最新版。

## 常用命令

### 分配任务

```text
/skill yunxiao-development-delivery
分配任务:任务=ONEOS-456 负责人=李振 计划开始=2026-07-27 计划完成=2026-07-28 预计工时=8
```

### 开始开发

```text
/skill yunxiao-development-delivery
/go 开始开发:任务=ONEOS-789
```

### 批量开发

```text
/skill yunxiao-development-delivery
/go 实现所有负责人是我的开发任务
```

### 修复单个 Bug

```text
/skill yunxiao-development-delivery
/go 修复bug:ONEOS-123
```

### 批量修复 Bug

```text
/skill yunxiao-development-delivery
/go 修复负责人是我的所有bug
```

### 完成开发

```text
/skill yunxiao-development-delivery
/go 完成开发:任务=ONEOS-789
```

## 仓库结构

```text
skills/
└── yunxiao-development-delivery/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    └── references/
```

Skill 运行时可能操作云效工作项、代码仓库、分支和合并请求。安装和使用前请检查仓库内容，并确保当前账号拥有相应项目权限。
