# /proofread

## 用途
只读检查.tex/.qmd的语法、拼写、溢出、术语一致性，生成报告不修改源文件

## 用法
```bash
/proofread [文件名或"all"]
```

## 检查项目
1. **语法检查** - LaTeX命令语法
2. **拼写检查** - 英文拼写错误
3. **溢出检查** - 文本超出边界
4. **术语一致性** - 术语使用统一
5. **格式规范** - 格式是否符合要求

## 参数
- `filename`: 文件名或"all"检查所有文件

## 示例
```bash
/proofread Lecture01.tex
/proofread all
/proofread Chapter03.qmd
```

## 输出
生成详细的检查报告，不修改源文件
