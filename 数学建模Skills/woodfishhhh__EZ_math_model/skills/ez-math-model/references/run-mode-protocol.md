# Run Mode Protocol

ez-math-model 的每次运行必须显式处于 `formal`、`demo` 或 `blocked` 三种模式之一。
运行模式决定代码是否可以求解、论文是否能写正式结论、质量门是否允许通过。

## 模式定义

| run_mode | 定义 | 是否可写正式结论 | 是否可打包 |
|---|---|---|---|
| `formal` | 题面与必要数据齐全，结果来自真实附件或用户确认的数据源 | 是 | 是 |
| `demo` | 缺关键数据，但用户明确允许用合成/示例数据验证流程 | 否，只能写流程验证 | 是，但标记为 demo |
| `blocked` | 缺关键输入，且用户未授权 demo | 否 | 否 |

## 必要附件判定

如果题面要求“附件中提供数据”“给出所有示例图结果”“按附件格式提交”等，而
`attachments/` 中没有对应 CSV、XLSX、JSON、TXT 或其他数据文件，默认判定：

```text
run_mode = blocked
reason = missing_required_attachments
```

只有用户明确说“先用合成数据演示 / 允许 demo / 先跑流程验证”，才可改为：

```text
run_mode = demo
formal_result = false
```

## 禁止静默 synthetic fallback

代码不得在 `formal` 模式下自动生成合成数据。若需要合成数据，必须同时满足：

1. `run_mode == demo`
2. `run_state.json.formal_result == false`
3. 结果表中有 `synthetic=true`
4. 论文和质量报告显式写明“非正式结果”

## run_state.json

每次运行必须生成：

```json
{
  "task_id": "...",
  "run_mode": "formal | demo | blocked",
  "formal_result": true,
  "setup_status": "user_confirmed | temporary_default | skipped | incomplete",
  "required_inputs": [],
  "missing_inputs": [],
  "can_generate_paper": true,
  "can_package": true,
  "created_at": "..."
}
```

## 质量门联动

- `formal` + `user_confirmed` 才能得到正式通过。
- `demo` 最高得到 `demo_pass`，不得写“正式结果通过”。
- `blocked` 必须停止在 intake 或 coding 前，输出阻塞诊断。
