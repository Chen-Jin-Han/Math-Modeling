---
name: scholar
description: |
  scholar 是 paper-search 的别名 / 软链。统一从这里入口可在内部代码中用更短的
  命名空间。本子 skill 的实际实现指向 tools/paper_search/。
read_when:
  - 任何与 paper-search 相同的场景
---

# scholar — paper-search 的别名入口

## 实际实现

请使用 `tools/paper_search/` 下的脚本与 SKILL.md。本目录仅作"短命名空间"
的入口占位。

```powershell
python tools/paper_search/scripts/openalex_scholar.py "<query>"
python tools/paper_search/scripts/aggregated_search.py "<query>"
```

## 为什么保留 scholar/ 这个目录

- 与 `references/external-tools-catalog.md` § 2 的"学术搜索"域命名一致
- 未来可能挂"按引用图谱回溯"等更专属的高级搜索脚本

## 不要在这里写代码

如有新脚本，写到 `tools/paper_search/scripts/` 并在那里更新 SKILL.md。
