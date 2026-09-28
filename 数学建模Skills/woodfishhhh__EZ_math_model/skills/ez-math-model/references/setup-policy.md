# Setup Policy

Setup 是 ez-math-model 的用户授权入口，不是普通环境检查。首次运行时，Agent
必须让用户明确选择工具链、corpus、agent mode 与辅助 skills；未经用户确认，
不得写入永久 setup 状态。

## 硬门规则

在进入 pipeline 01 前必须检查：

```text
external/tools/setup_state.json
```

若文件不存在、JSON 无法解析、`setup_completed != true`，或用户明确要求重新
配置，必须进入交互式 setup。此时禁止解析题目、建模、写代码、写论文和打包。

## 永久配置与临时默认

永久配置只能来自用户明确确认。只有当用户选择并确认保存时，才允许写入：

```text
external/tools/setup_state.json
external/tools/.tools_decided
external/tools/<domain>.{yes,free,skip}
external/tools/agent_mode.{single,multi,hybrid}
external/tools/inherited_skills.{yes,recommended,skip}
```

如果当前宿主环境无法完成交互，而用户又要求继续执行，只允许使用本次临时默认。
临时默认必须写入本次 runtime：

```text
runtime/{task_id}/setup_assumptions.json
```

临时默认不得创建或修改 `external/tools/setup_state.json`，也不得创建
`.tools_decided`。这条规则防止 Agent 替用户签字，把一次临时猜测污染成永久设置。

## setup_status

每次运行必须在 `runtime/{task_id}/run_state.json` 与 `quality_report.md` 中记录：

| 状态 | 含义 | 最终质量等级 |
|---|---|---|
| `user_confirmed` | 用户已完成并保存 setup | 可正式通过 |
| `temporary_default` | 本次使用临时默认，未保存 | 最高 `provisional_pass` |
| `skipped` | 用户显式跳过 setup | 最高 `provisional_pass` |
| `incomplete` | setup 未完成 | 阻塞 |

## 推荐临时默认

临时默认仅用于本次运行：

```json
{
  "pdf": "free-only",
  "scholar": "free-only",
  "dataset": "skip unless required by problem",
  "webcrawl": "skip unless required by problem",
  "corpus": "skip",
  "agent_mode": "hybrid",
  "inherited_skills": "recommended"
}
```

这些默认必须写入 `setup_assumptions.json`，并在最终诊断中说明“未持久化”。

## Agent 红线

- 不得因为“默认不追问”绕过首次 setup。
- 不得在没有用户确认时写永久 marker。
- 不得把临时默认描述为用户选择。
- 不得让 `temporary_default` 运行获得正式通过结论。
