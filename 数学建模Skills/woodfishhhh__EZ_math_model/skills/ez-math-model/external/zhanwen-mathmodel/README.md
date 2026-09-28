# external/zhanwen-mathmodel

运行时占位目录，仓库默认为空。

## 用途

存放从上游公开仓库 `https://github.com/zhanwen/MathModel` 按需拉取的优秀论文与
模板，作为 ez-math-model 在「建模方案」与「论文撰写」阶段的参考资料来源。

## 何时被填充

- pipeline 阶段 `01-problem-intake` 完成后、`02-modeling-plan` 启动前。
- 通过 `scripts/install/fetch_zhanwen.ps1`（Windows）或 `fetch_zhanwen.sh`（POSIX）拉取。
- 拉取成功 → 写入 `.complete` 标记 + 时间戳。
- 拉取失败（无网/无 git/磁盘不足）→ 写入 `.failed` 标记，pipeline 走「内置模板兜底」分支。
- 用户选择永久跳过 → 写入 `.skip` 标记，整个 skill 后续永不再询问。

## 拉取范围（sparse checkout）

只拉以下子集，避免下载整个上游：

- `国赛论文/`
- `国赛试题/`
- `美赛论文/`
- `2024年数模悉知&论文模版/`
- `2025年数模悉知&论文模版/`
- `2024年最终获奖名单/`
- `数学建模Latex模版/`
- `README.md`

## 版权与来源声明

本目录所有内容（拉取后产生）版权归原作者所有，仅供 ez-math-model 在本机
学术参考使用。**不复制、不分发、不提交回 ez-math-model 仓库**（已通过
`.gitignore` 排除）。论文产出引用其中材料时应以学术引用形式致谢上游。

上游许可证以 zhanwen/MathModel 仓库声明为准。
