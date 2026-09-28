# /standard-save

## 用途
五个评判标准并行投票，决定哪些[LEARN]条目升级到MEMORY.md

## 用法
```bash
/standard-save path.md
```

## 评判标准
1. **重要性** - 内容是否重要
2. **复用性** - 是否可复用
3. **准确性** - 内容是否准确
4. **完整性** - 内容是否完整
5. **独特性** - 是否有独特价值

## 投票机制
- 每个标准独立投票
- 多数通过则升级
- 保留原始条目

## 参数
- `path`: 文件路径

## 示例
```bash
/standard-save learn_notes.md
/standard-save session_knowledge.md
```

## 输出
将有价值的条目升级到MEMORY.md
