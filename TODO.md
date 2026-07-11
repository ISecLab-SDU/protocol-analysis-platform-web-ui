# TODO

## ProtocolGuard 静态分析数据库命名问题

当前阶段只要求处理 ProtocolGuard 已经支持的那几个软件。后端不应该维护一套项目名分支映射来兼容核心逻辑；项目名如何参与 AST 提取、match-pass 和 violation check，应该由 ProtocolGuard 自己的核心业务逻辑保持一致。

本次问题暴露的是 ProtocolGuard 内部两个组件的数据库命名不一致：

- `program_slicing` 的 C++ match-pass 会按 `sqlite_` + `project_name` + `.db` 创建数据库文件。
- `inconsistency_detection/violation_check.py` 之前在 `[database].path` 是目录时硬编码读取 `sqlite_Sol.db`。

如果后端把页面里的 `SOL` 原样写入 `project_name`，旧逻辑下 match-pass 会生成 `sqlite_SOL.db`，但 `violation_check.py` 会读取 `sqlite_Sol.db`。实际结果是：

- 真正有 `rule_code_snippet` 表和切片结果的是 `sqlite_SOL.db`。
- `violation_check.py` 读到的是空的 `sqlite_Sol.db`，日志出现 `no such table: rule_code_snippet` 和 `No data read`。
- `rule_code_snippet.llm_response` 不会被写入。
- 后续 assertion generation 从数据库筛选 `llm_response != ''` 时拿到 0 条记录，因此不会生成 `cursorkleosr/task/task*.txt`。

当前修复方向：

1. `program_slicing` 创建数据库文件时，把 `project_name` 归一化为小写后拼接 `sqlite_<project_name>.db`。
2. `violation_check.py` 读取数据库文件时，也把 `[project].project_name` 归一化为小写后拼接同样的文件名。
3. 后端继续把用户选择的实现名写入 `config.toml`，不在后端维护 `SOL -> Sol` 这类兼容映射。

后续仍需确认所有已支持软件的 `project_name` 都能被 `helper_scripts/build_ast_command.py` 的项目专用分支识别；这个限制属于 ProtocolGuard 当前核心业务边界，而不是后端兼容层应该兜底的问题。
