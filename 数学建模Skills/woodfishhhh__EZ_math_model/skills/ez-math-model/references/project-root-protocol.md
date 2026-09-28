# Project Root Protocol

ez-math-model 面向“项目总文件夹”运行。用户只需要新建一个总文件夹，把题目、
需求和补充资料放进去，然后在该目录打开 Codex / Claude Code。

## 标准目录

```text
项目总文件夹/
├── 用户输入/
├── runtime/
└── output/
    ├── source code/
    ├── paper/
    └── 附件文件夹/
```

## 目录职责

| 目录 | 职责 |
|---|---|
| `用户输入/` | 用户放入的题面、需求、补充数据、参考资料；Agent 只读或复制，不覆盖 |
| `runtime/` | 每次运行的中间产物、日志、临时数据、诊断、manifest |
| `output/source code/` | 可复用源代码、配置、运行说明 |
| `output/paper/` | 最终论文四格式：Markdown、DOCX、TXT、PDF |
| `output/附件文件夹/` | 图表、结果表、参考资料、提交附件 |

最终压缩包位于项目总文件夹根目录：

```text
output.zip
```

`output.zip` 必须包含项目总文件夹内的全部内容（`用户输入/`、`runtime/`、`output/`
等），但排除 `output.zip` 自身、临时 zip、`runtime/*/deliverable.zip` 历史兼容包，
避免递归打包和 stale artifact 嵌套。

## 根目录识别

`project_root` 优先级：

1. 用户显式给出的总文件夹路径。
2. 当前 Codex / Claude Code 工作目录。
3. 若用户只给单个题面文件，则取该文件所在目录；必要时创建标准子目录。

禁止默认把工作目录创建在 skill 安装目录下。skill 安装目录只读作协议与模板来源。

## 路径落盘

每次运行必须写入：

```text
runtime/{task_id}/project_paths.json
```

示例：

```json
{
  "project_root": "C:/.../MyModelProject",
  "input_root": "C:/.../MyModelProject/用户输入",
  "runtime_root": "C:/.../MyModelProject/runtime",
  "task_dir": "C:/.../MyModelProject/runtime/20260520-...",
  "output_root": "C:/.../MyModelProject/output",
  "paper_output": "C:/.../MyModelProject/output/paper",
  "source_output": "C:/.../MyModelProject/output/source code",
  "attachments_output": "C:/.../MyModelProject/output/附件文件夹"
}
```

## 兼容旧 workdir

旧版 `workdir/{task_id}` 视为 `runtime/{task_id}` 的兼容别名。新运行必须优先使用
`runtime/`。如果用户明确要求旧结构，可以保留 `workdir/`，但最终交付仍必须同步到
`output/`。
