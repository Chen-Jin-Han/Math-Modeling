# external/tools

工具决策状态目录。仓库默认仅含 `.gitkeep` 和本说明，运行时由 pipeline 00 写入
`setup_state.json`，记录用户是否已经走过首次 setup 以及外部工具选择。

`setup_state.json` 是 setup gate 的唯一主标记。没有它，或其中
`setup_completed` 不是 `true`，agent 必须重新执行首次 setup 提问。

## 标记文件

| 文件 | 含义 |
|---|---|
| `setup_state.json` | setup 是否完成、完成时间、7 个能力域的用户选择 |
| `.tools_decided` | 旧版兼容标记；不能替代 `setup_state.json` |
| `<domain>.free` | 该域只用免费 / 零配置工具（pdf / scholar / dataset / webcrawl） |
| `<domain>.skip` | 该域本次跳过 |
| `tools_decision_log.md` | 决策时间 / 用户选择 / 当时 env var 状态 |

七个 domain：`pdf`、`scholar`、`dataset`、`webcrawl`、`corpus`、`agent_mode`、
`inherited_skills`。

## 与 git 的关系

`.gitignore` 已排除 `external/tools/*` 但保留 `.gitkeep`，运行时产生的标记
文件不会被追踪。

## 与 catalog 的关系

工具元信息（价格 / 配置 / 何时启用）单一信息源是
`references/external-tools-catalog.md`；本目录只保存"用户决策快照"。
