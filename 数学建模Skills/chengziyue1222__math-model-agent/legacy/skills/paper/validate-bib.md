# /validate-bib

## 用途
验证引用与bibliography的完整性

## 用法
```bash
/validate-bib -semantic
```

## 检查模式
1. **默认模式** - 检查缺失/未用条目
2. **语义模式** - 增加DOI验证和引用漂移检测

## 检查项目
1. **缺失引用** - 正文引用但bib中缺失
2. **未用条目** - bib中存在但未被引用
3. **格式规范** - 引用格式是否统一
4. **DOI验证** - 验证DOI有效性（语义模式）
5. **引用漂移** - 检测引用内容漂移（语义模式）

## 参数
- `-semantic`: 启用语义检查模式

## 示例
```bash
/validate-bib
/validate-bib -semantic
```

## 输出
生成引用完整性报告，列出所有问题
