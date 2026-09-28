# /extract-tikz

## 用途
从Beamer源文件中提取TikZ图表 → 编译PDF → 转SVG

## 用法
```bash
/extract-tikz Lecture2
```

## 功能说明
- 从Beamer源文件中提取TikZ代码
- 编译为PDF格式
- 转换为SVG矢量图
- 便于在其他文档中复用

## 参数
- `filename`: Beamer文件名

## 示例
```bash
/extract-tikz Lecture2
/extract-tikz Chapter01_Diagrams
```
