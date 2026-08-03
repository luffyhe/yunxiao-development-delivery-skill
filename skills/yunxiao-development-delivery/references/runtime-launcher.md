# 跨平台脚本启动器

文档和后续动作统一写成：

```text
skill-run <script.py> [参数...]
```

`skill-run`是逻辑口令，不要求员工额外安装同名系统命令。执行当前Skill的Agent必须将其解析为本Skill自带启动器：Windows使用`scripts/run-skill-script.ps1`，macOS/Linux使用`scripts/run-skill-script.sh`。

启动器只允许运行同一`scripts`目录中的`.py`文件，拒绝绝对路径、相对目录和路径穿越；只选择通过版本检查的Python 3；临时目录通过系统运行时获取；原样返回脚本输出和退出码。Python 3、官方CLI、devops插件、脚本或认证变量不存在时明确失败，不得改走浏览器、连接器或网页内部接口。

云效CLI由脚本从`ALIYUN_CLI_PATH`或系统`PATH`解析；Windows额外检查当前用户`LocalAppData/AliyunCLI/aliyun.exe`。`分配任务`调用`yunxiao_cli_allocate_task.py`，批量Bug调用对应Bug适配器。不得在交接信息中传递另一客户端或另一Skill的安装路径。
