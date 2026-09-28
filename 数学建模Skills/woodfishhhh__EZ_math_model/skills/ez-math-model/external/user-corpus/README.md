# external/user-corpus

> **用户自带参考资料投放区**。把你想让 ez-math-model 参考的论文、教材、笔记、
> 历年题解，原样拖进来即可。不限文件名、不限层级、不限格式。

## 怎么用

1. 把任意 PDF / DOCX / Markdown / TXT / 笔记图片，**直接拖进本目录**。
   - 可以建子目录组织（`my-thesis/`、`week3/`、`MCM-2024-A/` 等）。
   - 文件名用中文、英文都行。
2. 在对话中说「reload corpus」或开始新任务，pipeline 01 会派一个 corpus
   explorer subagent 扫描本目录。
3. explorer 在本目录写出 `AGENTS.md`，供后续 modeler / writer 读取。

## 支持的文件类型

| 类型 | 处理方式 |
|---|---|
| `.pdf` | MinerU（首选）/ 宿主 pdf skill / pdfplumber 提取首尾 + 摘要 |
| `.docx` `.doc` | docx skill → 纯文本提取 |
| `.md` `.txt` | 直接读 |
| `.html` | 用 readability 类工具 → markdown |
| `.png` `.jpg` `.jpeg` | 让 LLM 视觉直读（笔记图、题面截图） |
| `.csv` `.xlsx` | 仅识别为"数据样本"，不进 corpus 摘要；如要当数据集，请放到任务的 `attachments/` |
| `.zip` `.tar.gz` | 不自动解压；先解开再放入 |

## explorer 产出

固定在本目录根：

- `AGENTS.md` — 给 modeler / writer 读的参考资料索引（文件清单 + 每篇 1-3 句
  摘要 + 与建模题型的关联标签）
- `.corpus_index.json` — explorer 内部缓存（文件 hash + mtime + 摘要）

`AGENTS.md` 每次运行都会被重写以反映最新文件集合，不要手动编辑。

## 与 git 的关系

`.gitignore` 已排除 `external/user-corpus/*` 全部内容（除 `.gitkeep` 与本
README）。你的私人参考材料**不会被仓库追踪**。

## 与 zhanwen 上游的区别

| 维度 | zhanwen/MathModel | user-corpus |
|---|---|---|
| 来源 | 公共 GitHub 上游 | 你本机自带 |
| 触发 | pipeline 02 询问拉取 | pipeline 00 询问启用 |
| 匹配 | 按赛事 / 年份 / 题号 | 按文件级摘要 + LLM 关联判断 |
| 文档载体 | thesis_match.json | AGENTS.md |

二者**互补**。zhanwen 给"高分论文范式"，user-corpus 给"你认可的资料"。

## 隐私与边界

- explorer 不上传文件到任何外部服务。
- 如果文件过大（>50MB / >100 页），explorer 仅读首尾各若干页 + 摘要。
- 含 token / 密码 / 个人隐私的文件**不要**放进来；explorer 会原样读取。
- 仓库默认不限制内容审查；放什么由你负责。

